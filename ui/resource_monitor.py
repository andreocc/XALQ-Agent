from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import QThread, Signal
import time

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class MonitorThread(QThread):
    usage_update = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True

    def run(self):
        if not PSUTIL_AVAILABLE:
            return
        while self._is_running:
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                self.usage_update.emit(cpu, ram)
            except Exception:
                break

    def stop(self):
        self._is_running = False
        self.wait()

class ResourceMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

        # Both white by default
        self.STYLE_NORMAL = "color: #FFFFFF; font-size: 11px; font-weight: bold; background: transparent;"
        self.STYLE_HIGH = "color: #FF6B6B; font-size: 11px; font-weight: bold; background: transparent;"

        self.lbl_cpu = QLabel("CPU: --%")
        self.lbl_ram = QLabel("RAM: --%")
        self.lbl_cpu.setStyleSheet(self.STYLE_NORMAL)
        self.lbl_ram.setStyleSheet(self.STYLE_NORMAL)

        self._layout.addWidget(self.lbl_cpu)
        self._layout.addWidget(self.lbl_ram)

        if PSUTIL_AVAILABLE:
            self.thread = MonitorThread(self)
            self.thread.usage_update.connect(self.update_labels)
            self.thread.start()
        else:
            self.lbl_cpu.setText("CPU: N/A")
            self.lbl_ram.setText("RAM: N/A")

    def update_labels(self, cpu, ram):
        self.lbl_cpu.setText(f"CPU: {cpu:.1f}%")
        self.lbl_ram.setText(f"RAM: {ram:.1f}%")

        # Only turn red on extreme usage, otherwise stay white
        self.lbl_cpu.setStyleSheet(self.STYLE_HIGH if cpu > 90 else self.STYLE_NORMAL)
        self.lbl_ram.setStyleSheet(self.STYLE_HIGH if ram > 90 else self.STYLE_NORMAL)

    def closeEvent(self, event):
        if hasattr(self, 'thread'):
            self.thread.stop()
        super().closeEvent(event)
