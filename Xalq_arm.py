import sys
import os
import platform
import logging

# Set up logging for ARM diagnostics
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("XALQ-ARM")

def optimize_for_arm():
    """Apply optimizations for Windows on ARM (Snapdragon X Elite/Plus)"""
    is_arm = platform.machine().lower() in ['arm64', 'aarch64']
    is_windows = sys.platform == 'win32'
    
    if is_arm and is_windows:
        logger.info("Windows on ARM detected. Applying native optimizations...")
        
        # Priority for NPU/GPU execution providers in ONNX Runtime
        os.environ["ORT_LOGGING_LEVEL"] = "1"
        
        # Hint for Qualcomm NPU (if using QNN EP)
        # Note: QNN_SDK_ROOT would typically be set by the user or installer
        if "QNN_SDK_ROOT" not in os.environ:
            logger.info("QNN_SDK_ROOT not found. NPU acceleration might need manual configuration.")

        # PySide6 optimizations for ARM
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
        os.environ["QT_API"] = "pyside6"

# Ensure the root directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow
except ImportError as e:
    logger.error(f"Error importing components: {e}")
    print("\nCertifique-se de instalar as dependências: pip install -r requirements_arm.txt")
    sys.exit(1)

def main():
    optimize_for_arm()
    
    app = QApplication(sys.argv)
    
    # Set Metadata
    app.setApplicationName("XALQ Agent (ARM Native)")
    app.setApplicationVersion("1.0.0-arm")
    app.setOrganizationName("XALQ")

    # Set Style (Windows default is usually fine, 'Fusion' is a good cross-platform alternative)
    app.setStyle("Fusion")

    # Show Main Window
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Unhandled exception in GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
