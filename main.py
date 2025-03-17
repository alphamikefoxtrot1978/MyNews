import sys
import os
import platform
os.environ["QT_FONT_DPI"] = "96" # FIX Problem for High DPI and Scale above 100%
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QTextEdit, QProgressBar, QCheckBox, QMenuBar, QTabWidget, QMessageBox, QDialog, QFrame
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QIcon, QAction, QTextCharFormat, QTextCursor, QFont, QColor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PIL import Image, ImageDraw
from io import BytesIO
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tweepy
import feedparser
import requests
import pyperclip
import time
import json
import logging
import re
from datetime import datetime

# Custom threads and dialogs
from threads.webpage_fetch import WebpageFetchThread
from threads.fetch_news import FetchNewsThread
from threads.image_preprocessing import ImagePreprocessingThread
from threads.chrome_driver import ChromeDriverThread
from threads.scheduler import SchedulerThread
from threads.log_update import LogUpdateThread
from dialogs.preferences import PreferencesDialog
from dialogs.schedule import ScheduleDialog


# Setup logging
logging.basicConfig(filename='news_poster.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

APP_VERSION = "1.3"
YOUR_NAME = "Alpha Mike Foxtrot"
X_USERNAME = "your_x_username"

class NewsPosterApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.news_data = []
        self.selected_news = []  # Tracks articles in queue_list
        self.selected_news_indices = []  # Tracks indices in queue_list
        self.driver = None
        self.article_cache = {}
        self.schedule_interval = None
        self.scheduler_timer = None
        self.log_update_thread = None
        self.fetch_threads = {}
        self.current_preview_url = None
        self.web_view = QWebEngineView()

        self.config_file = "config.json"
        self.load_config()

        self.setWindowTitle("News Poster")
        self.set_app_icon()

        # Setup UI
        self.setup_ui()
        self.start_log_update_thread()
        self.update_fetch_cached_button()

    def load_config(self):
        defaults = {
            "quora_email": "",
            "quora_password": "$",
            "twitter_api_key": "",
            "twitter_api_secret": "",
            "twitter_access_token": "",
            "twitter_access_secret": "",
            "logo_url": r"D:\Desktop\MyNews\new_york_post_logo.png",
            "output_image_url": r"D:\Desktop\MyNews\output.png",
            "quora_groups": ["https://fubarmemesandmusic.quora.com/"],
            "predefined_selection": []
        }
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = defaults
        self.quora_email = self.config["quora_email"]
        self.quora_password = self.config["quora_password"]
        self.twitter_api_key = self.config["twitter_api_key"]
        self.twitter_api_secret = self.config["twitter_api_secret"]
        self.twitter_access_token = self.config["twitter_access_token"]
        self.twitter_access_secret = self.config["twitter_access_secret"]
        self.logo_url = self.config["logo_url"]
        self.output_image_url = self.config["output_image_url"]
        self.quora_groups = self.config["quora_groups"]
        try:
            self.predefined_selection = [int(idx) for idx in self.config["predefined_selection"] if str(idx).isdigit()]
        except (ValueError, TypeError, KeyError) as e:
            logging.warning(f"Invalid predefined_selection in config: {e}. Resetting to empty list.")
            self.predefined_selection = []

    def save_config(self):
        self.config = {
            "quora_email": self.quora_email,
            "quora_password": self.quora_password,
            "twitter_api_key": self.twitter_api_key,
            "twitter_api_secret": self.twitter_api_secret,
            "twitter_access_token": self.twitter_access_token,
            "twitter_access_secret": self.twitter_access_secret,
            "logo_url": self.logo_url,
            "output_image_url": self.output_image_url,
            "quora_groups": self.quora_groups,
            "predefined_selection": self.predefined_selection
        }
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)

    def set_app_icon(self):
        try:
            self.setWindowIcon(QIcon(r"D:\Desktop\MyNews\default_icon.png"))
        except Exception as e:
            logging.error(f"Failed to set app icon: {e}")
            self.status_label.setText("Using default icon (Free tier)")

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Articles List
        left_panel = QWidget()
        left_layout_inner = QVBoxLayout(left_panel)
        left_layout_inner.setContentsMargins(5, 5, 5, 5)
        left_layout_inner.addWidget(QLabel("Articles"))

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_input = QLineEdit()
        self.filter_input.textChanged.connect(self.filter_articles)
        filter_layout.addWidget(self.filter_input)
        left_layout_inner.addLayout(filter_layout)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        # Connect selection change signal to update queue_list
        self.list_widget.itemSelectionChanged.connect(self.update_queue_list)
        left_layout_inner.addWidget(self.list_widget, stretch=1)

        left_panel.setLayout(left_layout_inner)
        top_layout.addWidget(left_panel, stretch=2)

        # Right Panel (Buttons and Queue List)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        self.fetch_button = QPushButton("Fetch News")
        self.fetch_button.clicked.connect(self.fetch_news)
        right_layout.addWidget(self.fetch_button)

        self.fetch_cached_button = QPushButton("Fetch News Cached")
        self.fetch_cached_button.clicked.connect(self.fetch_news_cached)
        right_layout.addWidget(self.fetch_cached_button)

        self.post_now_button = QPushButton("Post Now")
        self.post_now_button.clicked.connect(self.post_now)
        right_layout.addWidget(self.post_now_button)

        self.schedule_button = QPushButton("Schedule Posts")
        self.schedule_button.clicked.connect(self.schedule_posts)
        right_layout.addWidget(self.schedule_button)

        self.save_button = QPushButton("Save Selection")
        self.save_button.clicked.connect(self.save_selections)
        right_layout.addWidget(self.save_button)

        self.load_button = QPushButton("Load Selection")
        self.load_button.clicked.connect(self.load_selections)
        right_layout.addWidget(self.load_button)

        self.tabs = QTabWidget()
        self.queue_list = QListWidget()
        self.queue_list.itemClicked.connect(self.show_article_preview)
        self.tabs.addTab(self.queue_list, "Queue")
        right_layout.addWidget(self.tabs, stretch=1)

        right_panel.setLayout(right_layout)
        top_layout.addWidget(right_panel, stretch=1)

        # iPhone 14 Pro Max Preview
        preview_container = QFrame()
        preview_container.setStyleSheet("""
            QFrame {
                background-color: #000;
                border: 10px solid #333;
                border-radius: 20px;
            }
        """)
        preview_layout = QVBoxLayout(preview_container)
        self.web_view.setMinimumSize(430, 932)
        self.web_view.setMaximumSize(430, 932)
        preview_layout.addWidget(self.web_view)
        top_layout.addWidget(preview_container, stretch=1)

        left_layout.addLayout(top_layout)
        main_layout.addWidget(left_container, stretch=3)

        # Bottom Panel (Logs, Checkboxes, Progress)
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(5, 5, 5, 5)

        self.logs_label = QLabel("Logs")
        bottom_layout.addWidget(self.logs_label)
        self.logs_text = QTextEdit()
        self.logs_text.setMaximumHeight(100)
        self.logs_text.setFont(QFont('Consolas, "Courier New", monospace', 10))
        bottom_layout.addWidget(self.logs_text)

        self.post_to_x = QCheckBox("Post to X (Title + Link + Image)")
        self.post_to_x.setChecked(True)
        bottom_layout.addWidget(self.post_to_x)

        self.post_to_quora = QCheckBox("Post to Quora (Formatted)")
        self.post_to_quora.setChecked(True)
        bottom_layout.addWidget(self.post_to_quora)

        bottom_panel.setLayout(bottom_layout)
        left_layout.addWidget(bottom_panel)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Fetch Progress:"))
        self.fetch_progress = QProgressBar()
        self.fetch_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                color: #FFF;
            }
            QProgressBar::chunk {
                background-color: #1e90ff; /* Dodger Blue */
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.fetch_progress)
        progress_layout.addWidget(QLabel("Post Progress:"))
        self.post_progress = QProgressBar()
        self.post_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                color: #FFF;
            }
            QProgressBar::chunk {
                background-color: #1e90ff; /* Dodger Blue */
            }
        """)
        progress_layout.addWidget(self.post_progress)
        left_layout.addLayout(progress_layout)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_label)

    def update_fetch_cached_button(self):
        cache_file = "news_cache.json"
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
            self.fetch_cached_button.setEnabled(bool(data))
        else:
            self.fetch_cached_button.setEnabled(False)

    def start_log_update_thread(self):
        self.log_update_thread = LogUpdateThread(self, "news_poster.log")
        self.log_update_thread.log_updated.connect(self.update_logs)
        self.log_update_thread.start()

    def stop_log_update_thread(self):
        if self.log_update_thread:
            self.log_update_thread.stop()
            self.log_update_thread.wait()

    def update_list_widget(self):
        self.list_widget.clear()
        filter_text = self.filter_input.text().lower()
        for i, news in enumerate(self.news_data):
            if not filter_text or filter_text in news['title'].lower():
                self.list_widget.addItem(f"{i}: {news['title']}")
        for idx in self.predefined_selection:
            if idx < self.list_widget.count():
                self.list_widget.item(idx).setSelected(True)

    def filter_articles(self):
        self.update_list_widget()

    def update_queue_list(self):
        """Update queue_list based on the current selection in list_widget."""
        selected_items = self.list_widget.selectedItems()
        selected_indices = [int(item.text().split(":")[0]) for item in selected_items]

        # Create a new list of articles to be in the queue
        new_selected_news = []
        new_selected_indices = []
        new_queue_items = []

        for idx in selected_indices:
            if 0 <= idx < len(self.news_data):
                news_item = self.news_data[idx]
                new_selected_news.append(news_item)
                new_selected_indices.append(idx)
                new_queue_items.append(f"- {news_item['title']}")

        # Update the data structures
        self.selected_news = new_selected_news
        self.selected_news_indices = new_selected_indices

        # Update the queue_list UI
        self.queue_list.clear()
        for item in new_queue_items:
            self.queue_list.addItem(item)

        # Log the action
        if selected_items:
            last_added = self.selected_news[-1]['title'] if self.selected_news else "None"
            logging.info(f"Updated queue list. Last added: {last_added}")
            self.status_label.setText(f"Queue updated. Last added: {last_added}")
        else:
            logging.info("Queue list cleared (no articles selected)")
            self.status_label.setText("Queue cleared")

    def download_image(self, url_or_path):
        logging.info(f"Attempting to download image from: {url_or_path}")
        if os.path.isfile(url_or_path):
            try:
                img = Image.open(url_or_path).convert("RGBA")
                logging.info(f"Successfully downloaded image from {url_or_path}")
                return img
            except Exception as e:
                logging.error(f"Failed to load local image from {url_or_path}: {e}")
                return None
        try:
            response = requests.get(url_or_path, timeout=300)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content)).convert("RGBA")
                logging.info(f"Successfully downloaded image from {url_or_path}")
                return img
            else:
                logging.error(f"Failed to download image from {url_or_path}: HTTP {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Failed to download image from {url_or_path}: {e}")
            return None

    def add_rounded_corners(self, im, radius):
        if im is None:
            return None
        rounded_mask = Image.new("L", im.size, 0)
        draw = ImageDraw.Draw(rounded_mask)
        draw.rounded_rectangle([(0, 0), im.size], radius=radius, fill=255)
        im.putalpha(rounded_mask)
        return im

    def add_logo(self, image_url, logo_url, margin=20):
        image = self.download_image(image_url)
        if image is None:
            image = Image.new("RGBA", (300, 200), (255, 255, 255, 0))

        aspect_ratio = image.width / image.height
        max_size = 1024
        if image.width > image.height:
            new_width = min(image.width, max_size)
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = min(image.height, max_size)
            new_width = int(new_height * aspect_ratio)

        image = image.resize((new_width, new_height), Image.LANCZOS)

        logo = self.download_image(logo_url)
        if logo is None:
            return image

        logo_width = image.width // 7
        logo_height = int(logo.height * (logo_width / logo.width))
        logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
        logo = self.add_rounded_corners(logo, radius=20)
        if logo is None:
            return image

        x_pos = image.width - logo_width - margin
        y_pos = image.height - logo_height - margin
        try:
            image.paste(logo, (x_pos, y_pos), logo)
            return image
        except Exception as e:
            logging.error(f"Failed to paste logo onto image: {e}")
            return image

    def show_preprocessing_dialog(self, total_items):
        dialog = QDialog(self)
        dialog.setWindowTitle("Preprocessing Images")
        dialog.setFixedSize(400, 150)
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)

        wait_label = QLabel("Please wait:")
        wait_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(wait_label)

        desc_label = QLabel("Downloading and preparing required resources/images")
        layout.addWidget(desc_label)

        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        layout.addWidget(progress_bar)

        dialog.show()
        return dialog, progress_bar

    def preprocess_images(self, callback):
        if not self.selected_news:
            callback()
            return

        dialog, progress_bar = self.show_preprocessing_dialog(len(self.selected_news))
        output_dir = os.path.dirname(self.output_image_url) if self.output_image_url else "downloaded_images"
        self.image_thread = ImagePreprocessingThread(self, self.selected_news, self.logo_url, output_dir)
        self.image_thread.progress.connect(progress_bar.setValue)
        self.image_thread.finished.connect(dialog.accept)
        self.image_thread.finished.connect(callback)
        self.image_thread.error.connect(self.show_error_message)
        self.image_thread.start()

    def check_captcha(self, driver):
        return "turnstile" in driver.page_source.lower() or "verify you are human" in driver.page_source.lower()

    def click_turnstile(self, driver):
        try:
            wait = WebDriverWait(driver, 10)
            captcha = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cf-turnstile")))
            checkbox = captcha.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
            ActionChains(driver).move_to_element(checkbox).click().perform()
            time.sleep(5)
            return True
        except Exception as e:
            logging.error(f"CAPTCHA click failed: {e}")
            return False

    def dologin(self, driver):
        try:
            email_field = driver.find_element(By.NAME, "email")
            password_field = driver.find_element(By.NAME, "password")
            email_field.send_keys(self.quora_email)
            password_field.send_keys(self.quora_password)
            password_field.send_keys(Keys.RETURN)
            driver.find_element(By.XPATH, '//button[contains(@class, "qu-bg--blue")]').click()
            time.sleep(10)
        except Exception as e:
            logging.error(f"Login failed: {e}")

    def simulate_writing(self, text, action_chain):
        for char in text:
            action_chain.send_keys(char).pause(0.0005)
        return action_chain

    def post_toquora(self, driver, content, group_urls, template):
        wait = WebDriverWait(driver, 60) #increases timeout to 60 seconds
        for group_url in group_urls:
            try:
                logging.info(f"Navigating to Quora group: {group_url}")
                driver.get(group_url)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))  # Wait for page load
                
                #CAPTCHA Handling
                if self.check_captcha(driver):
                    logging.info("CAPTCHA detected, attempting to solve...")
                    if not self.click_turnstile(driver):
                        raise Exception("Failed to handle CAPTCHA")
                    wait.until_not(EC.presence_of_element_located((By.CLASS_NAME, "cf-turnstile")))  # Wait for CAPTCHA to clear
                    
                # Locate and click the post trigger
                trigger_post_box = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "Post in ")]')))
                trigger_post_box.click()
                
                # Locate and interact with the post box
                post_box = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"]')))
                post_box.click()
                act = ActionChains(driver)

                # Clearing in case previous post failed
                logging.info(f"Clearing the previous junk (if any)")
                act.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
                act.key_down(Keys.DELETE).key_up(Keys.DELETE).perform()
                
                # Posting Title
                logging.info(f"Posting title: {content['title']}")
                pyperclip.copy(content['title'])
                act.key_down(Keys.CONTROL).send_keys("b").key_up(Keys.CONTROL).perform()
                self.simulate_writing(content['title'], act).perform()
                act.key_down(Keys.ENTER).key_up(Keys.ENTER).perform()
                act.key_down(Keys.ENTER).key_up(Keys.ENTER).perform()
                
                # Posting summary
                summ = content['summary'].strip('[]')
                act.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys('9').key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
                self.simulate_writing(summ, act).perform()
                act.key_down(Keys.ENTER).key_up(Keys.ENTER).perform()
                act.key_down(Keys.ENTER).key_up(Keys.ENTER).perform()
                
                # Posting Fullstory
                self.simulate_writing(content['fullstory'], act).perform()
                act.key_down(Keys.ENTER).key_up(Keys.ENTER).perform()
                
                # Posting link
                self.simulate_writing(content['link'], act).perform()
                act.key_down(Keys.ENTER).key_up(Keys.ENTER).perform()
                
                # Handle image upload 
                if content['image']:
                    try:
                        logging.info(f"Uploading image: {content['image']}")
                        image_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
                        image_input.send_keys(content['image'])
                        #wait.until(EC.presence_of_element_located((By.XPATH, '//img[contains(@src, "upload")]')))  # Confirm upload
                        logging.info("Waiting for Image to uploaded")
                        time.sleep(30)
                    except Exception as e:
                        logging.warning(f"Image upload failed: {e}")
                
                #Submit Button
                submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "qu-bg--blue")]')))
                submit_button.click()
                #wait.until(EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "posted")]')))  # Confirm posting
                logging.info(f"Posted to Quora: {content['title']}")
            
            except Exception as e:
                logging.error(f"Quora posting failed for {content['title']}: {str(e)}")
                raise  # Re-raise to let ChromeDriverThread handle it
        act.perform()

    def post_to_twitter(self, content, queue_index):
        try:
            client = tweepy.Client(
                consumer_key=self.twitter_api_key,
                consumer_secret=self.twitter_api_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_secret
            )
            tweet = f"{content['title']} {content['link']}"[:280]
            if content['image']:
                auth = tweepy.OAuthHandler(self.twitter_api_key, self.twitter_api_secret)
                auth.set_access_token(self.twitter_access_token, self.twitter_access_secret)
                api = tweepy.API(auth)
                media = api.media_upload(content['image'])
                client.create_tweet(text=tweet, media_ids=[media.media_id])
            else:
                client.create_tweet(text=tweet)
            logging.info(f"Posted to Twitter: {content['title']}")
            self.update_queue_status(queue_index, True)
        except Exception as e:
            logging.error(f"Twitter posting failed: {e}")
            self.update_queue_status(queue_index, False)

    def update_queue_status(self, index, success):
        item = self.queue_list.item(index)
        if success:
            item.setBackground(QColor("#50fa7b"))
            item.setForeground(QColor("#f8f8f2"))
            #self.remove_from_cache(index)
        else:
            item.setBackground(QColor("#ff5555"))
            item.setForeground(QColor("#f8f8f2"))

    def remove_from_cache(self, queue_index):
        cache_file = "news_cache.json"
        if not os.path.exists(cache_file):
            return

        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)

            news_index = self.selected_news_indices[queue_index]
            if news_index < len(cache_data):
                news_item = cache_data[news_index]
                image_path = news_item.get("image")
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                        logging.info(f"Deleted image: {image_path}")
                    except Exception as e:
                        logging.error(f"Failed to delete image {image_path}: {e}")

                cache_data.pop(news_index)
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f)

                self.selected_news_indices = [idx if idx < news_index else idx - 1 for idx in self.selected_news_indices]
                self.selected_news.pop(queue_index)
                self.queue_list.takeItem(queue_index)
                self.update_fetch_cached_button()

        except Exception as e:
            logging.error(f"Failed to update cache: {e}")

    def fetch_news(self):
        self.status_label.setText("Fetching news...")
        self.fetch_progress.setValue(0)
        self.fetch_thread = FetchNewsThread(self, use_cache=False)
        self.fetch_thread.progress.connect(self.fetch_progress.setValue)
        self.fetch_thread.finished.connect(self.on_fetch_finished)
        self.fetch_thread.start()

    def fetch_news_cached(self):
        self.status_label.setText("Fetching cached news...")
        self.fetch_progress.setValue(0)
        self.fetch_thread = FetchNewsThread(self, use_cache=True)
        self.fetch_thread.progress.connect(self.fetch_progress.setValue)
        self.fetch_thread.finished.connect(self.on_fetch_finished)
        self.fetch_thread.start()

    def on_fetch_finished(self, news_data):
        self.news_data = news_data
        self.update_list_widget()
        self.status_label.setText("News fetched")
        self.update_fetch_cached_button()

    def post_now(self):
        if not self.selected_news:
            QMessageBox.warning(self, "No Articles in Queue", "Please add articles to the queue by selecting them in the Articles list.")
            return

        if QMessageBox.Yes != QMessageBox.question(self, "Confirm", "Post the articles in the queue now?"):
            return

        if not self.post_to_x.isChecked() and not self.post_to_quora.isChecked():
            QMessageBox.warning(self, "No Platform", "Please select at least one platform (X or Quora).")
            return

        self.status_label.setText("Preparing resources...")
        self.preprocess_images(self.start_posting)

    def start_posting(self):
        self.status_label.setText("Starting posting...")
        self.post_progress.setValue(0)

        total_posts = len(self.selected_news)
        posted_articles = set()  # Track posted articles to avoid duplicates
        for i, news in enumerate(self.selected_news):
            article_id = f"{news['title']}_{news['link']}"
            if article_id in posted_articles:
                continue
            if self.post_to_x.isChecked():
                self.post_to_twitter(news, i)
                posted_articles.add(article_id)
            self.post_progress.setValue((i + 1) * 100 // total_posts)
            self.status_label.setText(f"Posting to X: {i + 1}/{total_posts}")
            QApplication.processEvents()

        if self.post_to_quora.isChecked():
            template = self.logs_text.toPlainText()
            self.chrome_thread = ChromeDriverThread(self, self.selected_news, self.quora_groups, template)
            self.chrome_thread.status.connect(self.status_label.setText)
            self.chrome_thread.progress.connect(self.post_progress.setValue)
            self.chrome_thread.post_status.connect(self.update_queue_status)
            self.chrome_thread.finished.connect(self.on_quora_posting_finished)
            self.chrome_thread.error.connect(self.show_error_message)
            self.chrome_thread.start()

        self.update_logs()

    def on_quora_posting_finished(self):
        self.status_label.setText("Posting complete")
        self.update_logs()

    def show_error_message(self, error_msg):
        QMessageBox.critical(self, "Error", error_msg)
        self.status_label.setText("Error occurred")
        if self.scheduler_timer:
            self.scheduler_timer.stop()
            self.scheduler_timer = None
        self.update_logs()

    def schedule_posts(self):
        if not self.selected_news:
            QMessageBox.warning(self, "No Articles in Queue", "Please add articles to the queue by selecting them in the Articles list.")
            return

        dialog = ScheduleDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        start_time = dialog.get_schedule_time()
        self.schedule_interval = dialog.get_interval()

        if QMessageBox.Yes != QMessageBox.question(self, "Confirm", f"Schedule these articles to start at {start_time.strftime('%Y-%m-%d %I:%M:%S %p')} with {self.schedule_interval} minute(s) interval?"):
            return

        if not self.post_to_x.isChecked() and not self.post_to_quora.isChecked():
            QMessageBox.warning(self, "No Platform", "Please select at least one platform (X or Quora).")
            return

        self.status_label.setText("Preparing resources...")
        self.preprocess_images(lambda: self.start_scheduling(start_time))

    def start_scheduling(self, start_time):
        template = self.logs_text.toPlainText()
        self.post_progress.setValue(0)

        self.scheduler_thread = SchedulerThread(
            self,
            start_time,
            self.schedule_interval,
            self.selected_news,
            self.quora_groups,
            template,
            self.post_to_x.isChecked(),
            self.post_to_quora.isChecked()
        )
        self.scheduler_thread.progress.connect(self.post_progress.setValue)
        self.scheduler_thread.status.connect(self.status_label.setText)
        self.scheduler_thread.next_run.connect(self.update_countdown)
        self.scheduler_thread.post_status.connect(self.update_queue_status)
        self.scheduler_thread.finished.connect(self.on_scheduling_finished)
        self.scheduler_thread.error.connect(self.show_error_message)
        self.scheduler_thread.start()

        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.timeout.connect(self.update_status_with_animation)
        self.scheduler_timer.start(200)

    def update_countdown(self, next_run_time):
        current_time = time.time()
        remaining_seconds = max(0, next_run_time - current_time)
        minutes = int(remaining_seconds // 60)
        seconds = int(remaining_seconds % 60)
        self.countdown_text = f"Next post in {minutes}m {seconds}s"

    def update_status_with_animation(self):
        if not hasattr(self, 'animation_index'):
            self.animation_index = 0
        animation = ["|", "/", "-", "\\"]
        if hasattr(self, 'countdown_text'):
            self.status_label.setText(f"{animation[self.animation_index]} {self.countdown_text}")
        else:
            self.status_label.setText(f"{animation[self.animation_index]} Scheduling...")
        self.animation_index = (self.animation_index + 1) % len(animation)

    def on_scheduling_finished(self):
        self.status_label.setText("Scheduling complete")
        if self.scheduler_timer:
            self.scheduler_timer.stop()
            self.scheduler_timer = None
        self.schedule_interval = None
        self.update_logs()

    def save_selections(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select articles to save.")
            return
        indices = [int(item.text().split(":")[0]) for item in selected_items]
        with open("selections.json", 'w') as f:
            json.dump(indices, f)
        self.status_label.setText("Selection saved")

    def load_selections(self):
        try:
            with open("selections.json", 'r') as f:
                indices = json.load(f)
            self.list_widget.clearSelection()
            for idx in indices:
                if idx < self.list_widget.count():
                    self.list_widget.item(idx).setSelected(True)
            self.status_label.setText("Selection loaded")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load selections: {e}")

    def setup_accounts(self):
        dialog = PreferencesDialog(self)
        dialog.exec()

    def predefine_selection(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select articles first.")
            return
        self.predefined_selection = [int(item.text().split(":")[0]) for item in selected_items]
        self.save_config()
        self.status_label.setText("Predefined selection saved")
        self.update_list_widget()

    def update_logs(self, new_content=""):
        self.logs_text.moveCursor(QTextCursor.End)
        cursor = self.logs_text.textCursor()

        if new_content:
            lines = new_content.split('\n')
        else:
            try:
                with open("news_poster.log", 'r') as f:
                    all_content = f.read()
                lines = all_content.split('\n')
                lines = [line for line in lines if line.strip()]
                if len(lines) > 100:
                    lines = lines[-100:]
            except Exception as e:
                self.logs_text.setPlainText(f"No logs available. Error: {str(e)}")
                return

        for line in lines:
            if not line:
                continue
            parts = line.split(' - ', 2)
            if len(parts) < 3:
                continue

            timestamp, level, message = parts
            line_start_pos = cursor.position()

            timestamp_format = QTextCharFormat()
            timestamp_format.setForeground(QColor("#6272a4"))
            cursor.insertText(timestamp + " - ", timestamp_format)

            level_format = QTextCharFormat()
            if "INFO" in level:
                level_format.setForeground(QColor("#50fa7b"))
            elif "ERROR" in level:
                level_format.setForeground(QColor("#ff5555"))
            cursor.insertText(level + " - ", level_format)

            message_format = QTextCharFormat()
            message_format.setForeground(QColor("#f8f8f2"))
            cursor.insertText(message, message_format)

            message_start_pos = line_start_pos + len(timestamp) + len(level) + 4
            cursor.setPosition(message_start_pos)
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            message_text = cursor.selectedText()

            number_format = QTextCharFormat()
            number_format.setForeground(QColor("#bd93f9"))
            for match in re.finditer(r'\b\d+\b', message_text):
                start, end = match.span()
                cursor.setPosition(message_start_pos + start)
                cursor.setPosition(message_start_pos + end, QTextCursor.KeepAnchor)
                cursor.mergeCharFormat(number_format)

            cursor.setPosition(self.logs_text.document().characterCount() - 1)
            cursor.insertText("\n")

        self.logs_text.moveCursor(QTextCursor.End)

    def show_article_preview(self, item):
        index = self.queue_list.row(item)
        if 0 <= index < len(self.selected_news):
            url = self.selected_news[index]['link']
            self.current_preview_url = url
            if url in self.article_cache:
                self.web_view.setHtml(self.article_cache[url])
            else:
                self.status_label.setText(f"Loading article preview: {self.selected_news[index]['title']}")
                fetch_thread = WebpageFetchThread(url)
                fetch_thread.webpage_fetched.connect(lambda u, html: self.on_webpage_fetched(u, html))
                fetch_thread.error.connect(self.on_webpage_error)
                self.fetch_threads[url] = fetch_thread
                fetch_thread.start()

    def on_webpage_fetched(self, url, html):
        if url == self.current_preview_url:
            self.article_cache[url] = html
            self.web_view.setHtml(html)
        self.status_label.setText("Ready")

    def on_webpage_error(self, url, error_msg):
        logging.error(f"Failed to fetch {url}: {error_msg}")
        if url == self.current_preview_url:
            self.status_label.setText("Error loading preview")

    def show_about(self):
        QMessageBox.information(self, "About", 
                                f"News Poster\nVersion: {APP_VERSION}\nCreated by: {YOUR_NAME}\n\n"
                                "Fetches news from NY Post, posts to Quora (formatted) and X (title + link + image).")

    def closeEvent(self, event):
        self.stop_log_update_thread()
        for thread in self.fetch_threads.values():
            if thread.isRunning():
                thread.quit()
                thread.wait()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("dark")
    window = NewsPosterApp()
    window.show()
    sys.exit(app.exec())