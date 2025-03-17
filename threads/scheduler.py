from PySide6.QtCore import QThread, Signal
import schedule
import undetected_chromedriver as uc
from datetime import datetime
import time
import logging

class SchedulerThread(QThread):
    progress = Signal(int)
    status = Signal(str)
    next_run = Signal(float)
    finished = Signal()
    error = Signal(str)
    post_status = Signal(int, bool)

    def __init__(self, parent, start_time, interval, news_items, quora_groups, template, post_to_x, post_to_quora):
        super().__init__(parent)
        self.start_time = start_time
        self.interval = interval
        self.news_items = news_items
        self.quora_groups = quora_groups
        self.template = template
        self.post_to_x = post_to_x
        self.post_to_quora = post_to_quora
        self.driver = None
        self.current_index = 0

    def post_next_item(self):
        if self.current_index >= len(self.news_items):
            return schedule.CancelJob

        news = self.news_items[self.current_index]
        success = True
        try:
            if self.post_to_x:
                self.parent().post_to_twitter(news, self.current_index)
        except Exception as e:
            logging.error(f"Twitter posting failed for {news['title']}: {e}")
            success = False

        try:
            if self.post_to_quora:
                self.parent().post_toquora(self.driver, news, self.quora_groups, self.template)
        except Exception as e:
            logging.error(f"Quora posting failed for {news['title']}: {e}")
            success = False

        self.post_status.emit(self.current_index, success)
        self.current_index += 1
        completed = self.current_index
        total_posts = len(self.news_items)
        self.progress.emit(completed * 100 // total_posts)
        self.status.emit(f"Scheduled: {completed}/{total_posts} posted")
        return None if self.current_index < len(self.news_items) else schedule.CancelJob

    def run(self):
        try:
            if self.post_to_quora:
                self.status.emit("Initializing ChromeDriver for Quora...")
                options = uc.ChromeOptions()
                options.add_argument("--start-maximized")
                self.driver = uc.Chrome(options=options)
                self.driver.get("https://www.quora.com/")
                time.sleep(10)
                self.parent().dologin(self.driver)

            current_time = datetime.now()
            if self.start_time > current_time:
                delay_seconds = (self.start_time - current_time).total_seconds()
                self.status.emit(f"Waiting until {self.start_time.strftime('%Y-%m-%d %I:%M:%S %p')} to start posting...")
                time.sleep(delay_seconds)

            schedule.clear()
            schedule.every(self.interval).minutes.do(self.post_next_item)

            self.status.emit("Scheduled. Running...")
            while self.current_index < len(self.news_items):
                schedule.run_pending()
                if schedule.jobs:
                    self.next_run.emit(schedule.next_run().timestamp())
                time.sleep(1)

            self.status.emit("Scheduling complete")
            self.finished.emit()

        except Exception as e:
            error_msg = f"Scheduling failed: {str(e)}"
            logging.error(error_msg)
            self.error.emit(error_msg)
            self.status.emit("Error during scheduling")

        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.status.emit("ChromeDriver closed")
                except Exception as e:
                    logging.error(f"Failed to close ChromeDriver: {e}")