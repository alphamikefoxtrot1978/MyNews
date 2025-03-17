from PySide6.QtCore import QThread, Signal
import feedparser
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import json
import os
import logging

class FetchNewsThread(QThread):
    progress = Signal(int)
    finished = Signal(list)

    def __init__(self, parent=None, use_cache=False):
        super().__init__(parent)
        self.use_cache = use_cache

    def run(self):
        cache_file = "news_cache.json"
        if self.use_cache and os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                news_data = json.load(f)
            self.progress.emit(100)
            self.finished.emit(news_data)
            return

        RSS_FEED_URL = "https://nypost.com/politics/feed/"
        feed = feedparser.parse(RSS_FEED_URL)
        news_data = []
        total_entries = len(feed.entries)

        def fetch_story(entry):
            title = entry.title
            link = entry.link
            summary = entry.summary if hasattr(entry, "summary") else "No summary available."
            image = entry.media_content[0]['url'] if hasattr(entry, "media_content") else None
            full_story = self.scrape_full_story(link)
            return {"title": title, "summary": summary, "fullstory": full_story, "link": link, "image": image}

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(fetch_story, entry) for entry in feed.entries]
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                news_data.append(future.result())
                self.progress.emit((i + 1) * 100 // total_entries)

        with open(cache_file, 'w') as f:
            json.dump(news_data, f)
        
        self.finished.emit(news_data)

    def scrape_full_story(self, url):
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=300)
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            full_story = "\n".join([p.get_text() for p in paragraphs if len(p.get_text()) > 50])
            return full_story if full_story else "Full story not available."
        except Exception as e:
            logging.error(f"Failed to scrape {url}: {e}")
            return f"❌ Error fetching story: {e}"