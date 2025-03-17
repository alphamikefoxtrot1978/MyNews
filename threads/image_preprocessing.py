from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication
import os
import json
import logging

class ImagePreprocessingThread(QThread):
    progress = Signal(int)
    finished = Signal()
    error = Signal(str)

    def __init__(self, parent, selected_news, logo_url, output_dir):
        super().__init__(parent)
        self.selected_news = selected_news
        self.logo_url = logo_url
        self.output_dir = output_dir
        self.news_poster_app = parent

    def run(self):
        try:
            total_items = len(self.selected_news)
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            for i, news in enumerate(self.selected_news):
                if news.get("image"):
                    image_filename = f"article_{i}.png"
                    local_image_path = os.path.join(self.output_dir, image_filename)
                    
                    output_image = self.news_poster_app.add_logo(news["image"], self.logo_url)
                    if output_image:
                        output_image.save(local_image_path)
                        news["image"] = local_image_path
                    else:
                        logging.warning(f"Failed to process image for {news['title']}")
                        news["image"] = self.logo_url
                
                self.progress.emit((i + 1) * 100 // total_items)
                QApplication.processEvents()

            cache_file = "news_cache.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    full_news_data = json.load(f)
                for i, news in enumerate(self.selected_news):
                    idx = self.news_poster_app.selected_news_indices[i]
                    full_news_data[idx]["image"] = news["image"]
                with open(cache_file, 'w') as f:
                    json.dump(full_news_data, f)

            self.finished.emit()
        except Exception as e:
            error_msg = f"Image preprocessing failed: {str(e)}"
            logging.error(error_msg)
            self.error.emit(error_msg)