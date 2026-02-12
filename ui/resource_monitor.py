import time
from PySide6.QtCore import QThread, Signal

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class ResourceMonitor(QThread):
    usage_update = Signal(float, float) # CPU %, RAM %

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True

    def run(self):
        if not PSUTIL_AVAILABLE:
            return

        while self._is_running:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                self.usage_update.emit(cpu, ram)
                time.sleep(1)
            except Exception:
                break
    
    def stop(self):
        self._is_running = False
        self.wait()
