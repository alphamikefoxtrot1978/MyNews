from PySide6.QtCore import QThread, Signal
import os
import time

class LogUpdateThread(QThread):
    log_updated = Signal(str)

    def __init__(self, parent, log_file):
        super().__init__(parent)
        self.log_file = log_file
        self.last_size = 0
        self.running = True

    def run(self):
        while self.running:
            if os.path.exists(self.log_file):
                current_size = os.path.getsize(self.log_file)
                if current_size > self.last_size:
                    with open(self.log_file, 'r') as f:
                        f.seek(self.last_size)
                        new_content = f.read()
                        if new_content:
                            self.log_updated.emit(new_content)
                    self.last_size = current_size
            time.sleep(0.1)

    def stop(self):
        self.running = False