from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import QThread, Signal, Qt, QTimer
import time

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class MonitorThread(QThread):
    usage_update = Signal(float, float) # CPU %, RAM %

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
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

        self.lbl_cpu = QLabel("CPU: --%")
        self.lbl_ram = QLabel("RAM: --%")
        
        # Style for mini-monitor
        style = "color: #6c7086; font-size: 11px; font-weight: bold;"
        self.lbl_cpu.setStyleSheet(style)
        self.lbl_ram.setStyleSheet(style)

        self.layout.addWidget(self.lbl_cpu)
        self.layout.addWidget(self.lbl_ram)

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
        
        # Color coding high usage
        if cpu > 80: self.lbl_cpu.setStyleSheet("color: #f38ba8; font-size: 11px; font-weight: bold;")
        else: self.lbl_cpu.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: bold;")

    def closeEvent(self, event):
        if hasattr(self, 'thread'):
            self.thread.stop()
        super().closeEvent(event)
