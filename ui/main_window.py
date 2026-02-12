import os
import sys
import webbrowser
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QComboBox, 
    QTextEdit, QProgressBar, QMessageBox, QFrame,
    QLineEdit, QDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer
from PySide6.QtGui import QIcon, QFont, QAction, QColor, QPalette

from core.worker_engine import WorkerEngine
from core.processing_worker import ProcessingWorker
from core.updater import Updater
from ui.settings_dialog import SettingsDialog
from ui.resource_monitor import ResourceMonitor

# --- Premium Stylesheet (Dark Blue/Grey) ---
DARK_THEME_QSS = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    font-size: 14px;
}
QFrame#MainContainer {
    background-color: #1e1e2e;
    border: none;
}
QFrame#Card {
    background-color: #262636;
    border-radius: 12px;
    border: 1px solid #313244;
}
QLabel {
    color: #cdd6f4;
}
QLabel#Title {
    font-size: 24px;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#Subtitle {
    font-size: 14px;
    color: #a6adc8;
}
QLabel#StatusFooter {
    font-size: 12px;
    color: #6c7086;
    padding: 5px;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}
QPushButton:pressed {
    background-color: #1e1e2e;
}
QPushButton#PrimaryButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
}
QPushButton#PrimaryButton:hover {
    background-color: #b4befe;
}
QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px;
    color: #cdd6f4;
}
QComboBox:hover {
    border-color: #585b70;
}
QComboBox::drop-down {
    border: none;
}
QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px;
    color: #cdd6f4;
}
QTextEdit {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 8px;
    color: #a6adc8;
    font-family: 'Consolas', 'Monospace';
    font-size: 13px;
    padding: 10px;
}
QProgressBar {
    background-color: #313244;
    border-radius: 6px;
    text-align: center;
    color: #cdd6f4;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 6px;
}
/* Scrollbar */
QScrollBar:vertical {
    border: none;
    background: #1e1e2e;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: none;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XALQ Agent Enterprise")
        self.setMinimumSize(1000, 700)
        
        # Apply Theme
        self.setStyleSheet(DARK_THEME_QSS)

        # Core Components
        self.worker_engine = WorkerEngine(progress_callback=self.update_log_from_worker)
        self.processing_thread = None
        self.updater = Updater(os.path.dirname(os.path.abspath(__file__)))
        
        self.setup_ui()
        self.check_local_version()
        
        # Async Version Check
        QTimer.singleShot(1000, self.check_remote_version)

    def setup_ui(self):
        # Main Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_h_layout = QHBoxLayout(main_widget)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # Content Area
        content_frame = QFrame()
        content_frame.setObjectName("MainContainer")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        main_h_layout.addWidget(content_frame)

        # --- Header ---
        header_layout = QHBoxLayout()
        
        title_container = QVBoxLayout()
        title = QLabel("XALQ Agent")
        title.setObjectName("Title")
        subtitle = QLabel("Enterprise Intelligence System")
        subtitle.setObjectName("Subtitle")
        title_container.addWidget(title)
        title_container.addWidget(subtitle)
        
        header_layout.addLayout(title_container)
        header_layout.addStretch()
        
        # Settings Button
        self.btn_settings = QPushButton("⚙ Configurações")
        self.btn_settings.clicked.connect(self.open_settings)
        header_layout.addWidget(self.btn_settings)

        # Resource Monitor (Mini)
        self.resource_monitor = ResourceMonitor()
        self.resource_monitor.setStyleSheet("background-color: transparent;")
        header_layout.addWidget(self.resource_monitor)
        
        content_layout.addLayout(header_layout)
        
        # Banner for Updates (Hidden by default)
        self.update_banner = QLabel("🚀 Nova versão disponível! Reinicie para aplicar.")
        self.update_banner.setStyleSheet("background-color: #a6e3a1; color: #1e1e2e; padding: 10px; border-radius: 6px; font-weight: bold;")
        self.update_banner.setAlignment(Qt.AlignCenter)
        self.update_banner.hide()
        content_layout.addWidget(self.update_banner)

        # --- Card: Input & Configuration ---
        config_card = QFrame()
        config_card.setObjectName("Card")
        card_layout = QVBoxLayout(config_card)
        card_layout.setContentsMargins(20, 20, 20, 20)

        # File Selection
        file_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("Selecione o arquivo de dados (.xlsx, .csv)...")
        self.file_path_input.setReadOnly(True)
        
        btn_select_file = QPushButton("📂 Selecionar Arquivo")
        btn_select_file.clicked.connect(self.select_file)
        
        file_layout.addWidget(self.file_path_input)
        file_layout.addWidget(btn_select_file)
        card_layout.addLayout(file_layout)
        
        # Options Grid
        opts_layout = QHBoxLayout()
        
        # Model Selection
        mdl_layout = QVBoxLayout()
        mdl_layout.addWidget(QLabel("Modelo Gemini:"))
        self.combo_model = QComboBox()
        # Default options, will try to fetch more
        self.available_models = ["gemini-1.5-pro", "gemini-2.0-flash", "gemini-1.5-flash"]
        self.combo_model.addItems(self.available_models)
        self.combo_model.setCurrentText("gemini-1.5-pro")
        mdl_layout.addWidget(self.combo_model)
        opts_layout.addLayout(mdl_layout)
        
        # Analysis Type
        type_layout = QVBoxLayout()
        type_layout.addWidget(QLabel("Tipo de Análise:"))
        self.combo_prompt_type = QComboBox()
        self.combo_prompt_type.addItems(["Automático (Detectar)", "revenue", "operations"])
        type_layout.addWidget(self.combo_prompt_type)
        opts_layout.addLayout(type_layout)
        
        card_layout.addLayout(opts_layout)
        content_layout.addWidget(config_card)

        # --- Action ---
        action_layout = QHBoxLayout()
        self.btn_process = QPushButton("▶ Iniciar Processamento")
        self.btn_process.setObjectName("PrimaryButton")
        self.btn_process.setFixedHeight(45)
        self.btn_process.clicked.connect(self.start_processing)
        action_layout.addWidget(self.btn_process)
        content_layout.addLayout(action_layout)

        # --- Logs ---
        content_layout.addWidget(QLabel("Logs de Execução:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        content_layout.addWidget(self.log_area)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6) # Slim
        content_layout.addWidget(self.progress_bar)

        # --- Footer ---
        self.lbl_status = QLabel("Inicializando...")
        self.lbl_status.setObjectName("StatusFooter")
        self.lbl_status.setAlignment(Qt.AlignRight)
        content_layout.addWidget(self.lbl_status)
        
        # Populate models async
        QTimer.singleShot(500, self.refresh_models)

    def check_local_version(self):
        try:
            with open(os.path.join(self.updater.base_dir, 'version.json'), 'r', encoding='utf-8') as f:
                import json
                v_data = json.load(f)
                self.local_version = v_data.get('version', 'Unknown')
                self.lbl_status.setText(f"XALQ v{self.local_version} | Status: Pronto")
        except:
             self.local_version = "Unknown"

    def check_remote_version(self):
        # Simple non-blocking update check logic simulated or via Updater
        # For now, let's trust Updater's logic if implemented, or just check JSON
        # Calling Updater synchronously here for simplicity as it's quick usually
        try:
            has_update, new_v = self.updater.check_for_updates()
            if has_update:
                self.update_banner.setText(f"🚀 Nova versão disponível ({new_v})! Reinicie para aplicar.")
                self.update_banner.show()
                # Auto-pull logic is in Updater, we just notify
        except Exception as e:
            print(f"Update check failed: {e}")

    def refresh_models(self):
        try:
            # Try to fetch real models from worker
            real = self.worker_engine.get_available_models()
            if real:
                current = self.combo_model.currentText()
                self.combo_model.clear()
                self.combo_model.addItems(real)
                # Restore selection or default to Pro
                idx = self.combo_model.findText(current)
                if idx >= 0:
                     self.combo_model.setCurrentIndex(idx)
                else:
                     # Default to 1.5-pro if available
                     idx_pro = self.combo_model.findText("gemini-1.5-pro")
                     if idx_pro >= 0: 
                         self.combo_model.setCurrentIndex(idx_pro)
        except:
            pass

    def select_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo", "", "Excel/CSV Files (*.xlsx *.csv)")
        if f:
            self.file_path_input.setText(f)
            self.log(f"Arquivo selecionado: {f}", "info")

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
        # Reload worker engine key
        self.worker_engine = WorkerEngine(progress_callback=self.update_log_from_worker)

    def start_processing(self):
        file_path = self.file_path_input.text()
        if not file_path:
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo primeiro.")
            return

        model = self.combo_model.currentText()
        prompt_type = self.combo_model_prompt_type_text()

        self.btn_process.setEnabled(False)
        self.progress_bar.setRange(0, 0) # Indeterminate pulsating
        self.lbl_status.setText(f"🧠 Processando via: {model}...")

        # Worker Thread
        self.processing_thread = QThread()
        self.worker = ProcessingWorker(self.worker_engine, file_path, model, prompt_type_override=prompt_type)
        self.worker.moveToThread(self.processing_thread)

        self.processing_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.progress.connect(self.update_log_from_worker)
        self.worker.error.connect(self.on_processing_error)

        self.processing_thread.start()

    def combo_model_prompt_type_text(self):
        txt = self.combo_prompt_type.currentText()
        if "Automático" in txt: return None
        return txt

    def on_processing_finished(self):
        self.btn_process.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.lbl_status.setText(f"XALQ v{self.local_version} | Status: Concluído")
        self.log("Processamento finalizado com sucesso.", "success")
        
        # Open output folder
        try:
             os.startfile(self.worker_engine.output_dir)
        except:
             pass

        self.processing_thread.quit()
        self.processing_thread.wait()

    def on_processing_error(self, err_msg):
        self.btn_process.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.lbl_status.setText(f"XALQ v{self.local_version} | Status: Erro")
        self.log(f"Erro: {err_msg}", "error")
        self.processing_thread.quit()
        self.processing_thread.wait()

    def update_log_from_worker(self, msg):
        # Detect type for coloring
        level = "info"
        if "erro" in msg.lower() or "falha" in msg.lower(): level = "error"
        elif "sucesso" in msg.lower() or "gerado" in msg.lower(): level = "success"
        elif "---" in msg: level = "highlight"
        
        self.log(msg, level)

    def log(self, message, level="info"):
        color = "#cdd6f4" # Default Text
        if level == "error": color = "#f38ba8" # Red
        elif level == "success": color = "#a6e3a1" # Green
        elif level == "highlight": color = "#89b4fa" # Blue
        elif level == "debug": color = "#6c7086" # Grey

        html = f'<span style="color:{color};">{message}</span>'
        self.log_area.append(html)
        # Auto scroll
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
