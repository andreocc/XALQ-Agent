import sys
import os
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QTimer

# Ensure the root directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from ui.main_window import MainWindow
except ImportError as e:
    try:
        from .ui.main_window import MainWindow
    except ImportError:
        print(f"Error importing UI: {e}")
        sys.exit(1)

def create_splash(logo_path):
    """Create a branded splash screen with the XALQ logo."""
    splash_w, splash_h = 420, 280
    pixmap = QPixmap(splash_w, splash_h)
    pixmap.fill(QColor("#1E293B"))  # Dark background matching app theme

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw logo centered
    if os.path.exists(logo_path):
        logo = QPixmap(logo_path).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (splash_w - logo.width()) // 2
        painter.drawPixmap(x, 40, logo)

    # App name
    painter.setPen(QColor("#FFFFFF"))
    font = QFont("Segoe UI", 22, QFont.Bold)
    painter.setFont(font)
    painter.drawText(0, 175, splash_w, 40, Qt.AlignCenter, "XALQ Agent")

    # Tagline
    painter.setPen(QColor("#94A3B8"))
    font2 = QFont("Segoe UI", 10)
    painter.setFont(font2)
    painter.drawText(0, 215, splash_w, 25, Qt.AlignCenter, "Reduzindo risco decisório com inteligência")

    # Version
    painter.setPen(QColor("#475569"))
    painter.drawText(0, 250, splash_w, 20, Qt.AlignCenter, "Carregando...")

    painter.end()
    return pixmap

def main():
    app = QApplication(sys.argv)

    # Set Metadata
    app.setApplicationName("XALQ Agent")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("XALQ")
    app.setStyle("Fusion")

    # Splash Screen
    logo_path = os.path.join(current_dir, 'templates', 'img', '0_XALQ-0.png')
    splash_pix = create_splash(logo_path)
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    # Build main window while splash is showing
    window = MainWindow()

    # Close splash and show main window after 2 seconds
    QTimer.singleShot(3000, lambda: (splash.close(), window.show()))

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
