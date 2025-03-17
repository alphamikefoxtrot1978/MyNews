from PySide6.QtCore import QThread, Signal
import requests

class WebpageFetchThread(QThread):
    webpage_fetched = Signal(str, str)
    error = Signal(str, str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            self.webpage_fetched.emit(self.url, response.text)
        except Exception as e:
            self.error.emit(self.url, f"Error fetching webpage: {str(e)}")