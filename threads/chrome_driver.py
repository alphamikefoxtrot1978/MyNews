from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication
import undetected_chromedriver as uc
import time
import logging

class ChromeDriverThread(QThread):
    status = Signal(str)
    progress = Signal(int)
    finished = Signal()
    error = Signal(str)
    post_status = Signal(int, bool)

    def __init__(self, parent, news_items, quora_groups, template):
        super().__init__(parent)
        self.news_items = news_items
        self.quora_groups = quora_groups
        self.template = template
        self.driver = None

    def run(self):
        try:
            self.status.emit("Initializing ChromeDriver...")
            options = uc.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            self.driver = uc.Chrome(options=options)
            self.driver.set_page_load_timeout(300)  # Increase to 5 minutes (300 seconds)
            self.driver.implicitly_wait(30)  # Implicit wait of 30 seconds for element lookups
            self.status.emit("ChromeDriver initialized, navigating to Quora...")
            self.driver.get("https://www.quora.com/")
            time.sleep(5)
            
            self.status.emit("Logging into Quora...")
            self.parent().dologin(self.driver)
            
            total_posts = len(self.news_items)
            for i, news in enumerate(self.news_items):
                self.status.emit(f"Posting to Quora: {i + 1}/{total_posts}")
                try:
                    self.parent().post_toquora(self.driver, news, self.quora_groups, self.template)
                    self.post_status.emit(i, True)
                except Exception as e:
                    logging.error(f"Quora posting failed for {news['title']}: {e}")
                    self.post_status.emit(i, False)
                self.progress.emit((i + 1) * 100 // total_posts)
                QApplication.processEvents()
            
            self.status.emit("Quora posting complete")
            self.finished.emit()
        
        except Exception as e:
            error_msg = f"ChromeDriver thread failed: {str(e)}"
            logging.error(error_msg)
            self.error.emit(error_msg)
            self.status.emit("Error during Quora posting")
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.status.emit("ChromeDriver closed")
                except Exception as e:
                    logging.error(f"Failed to close ChromeDriver: {e}")