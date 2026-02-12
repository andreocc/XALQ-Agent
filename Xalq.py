import sys
import os
from PySide6.QtWidgets import QApplication

# Ensure the root directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from ui.main_window import MainWindow
except ImportError as e:
    # Fallback to absolute import if running from a different context
    try:
        from .ui.main_window import MainWindow
    except ImportError:
        print(f"Error importing UI: {e}")
        sys.exit(1)

def main():
    app = QApplication(sys.argv)
    
    # Set Metadata
    app.setApplicationName("XALQ Agent")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("XALQ")

    # Set Style (Windows default is usually fine, 'Fusion' is a good cross-platform alternative)
    app.setStyle("Fusion")

    # Show Main Window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
