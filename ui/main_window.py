import os
import sys
import json
import requests
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QComboBox,
    QTextEdit, QProgressBar, QMessageBox, QFrame,
    QLineEdit, QStatusBar
)
from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QPixmap

from core.worker_engine import WorkerEngine
from core.processing_worker import ProcessingWorker
from core.updater import Updater
from ui.settings_dialog import SettingsDialog
from ui.resource_monitor import ResourceMonitor

# --- QSS: Brand Theme (Teal + Green) ---
BRAND_QSS = """
QMainWindow {
    background-color: #F8FAFC;
}

#headerFrame {
    background-color: #2BA8A0;
    border-bottom: 3px solid #8CC63F;
    min-height: 80px;
}

#appNameLabel {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: bold;
}

QGroupBox, QFrame#containerFrame {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}

QLabel {
    color: #1E293B;
}

QLineEdit, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px;
    color: #1E293B;
}

QLineEdit:focus {
    border: 2px solid #2BA8A0;
}

QComboBox::drop-down {
    border: none;
}

QPushButton#btnStart {
    background-color: #8CC63F;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 16px;
    border-radius: 8px;
    padding: 12px;
    border: none;
}

QPushButton#btnStart:hover {
    background-color: #7AB535;
}

QPushButton {
    background-color: #E2E8F0;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #CBD5E1;
}

QTextEdit#logArea {
    background-color: #1E293B;
    color: #8CC63F;
    font-family: 'Consolas', 'Monaco', monospace;
    border-radius: 8px;
    padding: 10px;
}

QProgressBar {
    background-color: #E2E8F0;
    border-radius: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #2BA8A0;
    border-radius: 4px;
}

QStatusBar {
    background-color: #F1F5F9;
    color: #64748B;
    border-top: 1px solid #E2E8F0;
}

QScrollBar:vertical {
    border: none;
    background: #F1F5F9;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 20px;
    border-radius: 4px;
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
        self.processing_thread = None
        self.local_version = "Unknown"
        self.github_connected = False

        self.setStyleSheet(BRAND_QSS)

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_root = project_root
        self.updater = Updater(project_root)

        self.setup_ui()

        # Initialize Worker AFTER UI
        self.worker_engine = WorkerEngine(progress_callback=self.update_log_from_worker)

        self.check_local_version()
        QTimer.singleShot(500, self.load_prompts_from_disk)
        QTimer.singleShot(1000, self.check_remote_version)
        QTimer.singleShot(1500, self.check_github_connectivity)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # Logo
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'templates', 'img', '0_XALQ-0.png'
        )
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pix = QPixmap(logo_path).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
            logo_label.setStyleSheet("background: transparent;")
            header_layout.addWidget(logo_label)

        app_name = QLabel("XALQ Agent")
        app_name.setObjectName("appNameLabel")
        app_name.setStyleSheet("background: transparent;")
        header_layout.addWidget(app_name)
        header_layout.addStretch()

        # Resource Monitor (in header, right side)
        self.resource_monitor = ResourceMonitor()
        self.resource_monitor.setStyleSheet("background: transparent;")
        header_layout.addWidget(self.resource_monitor)

        main_layout.addWidget(header)

        # ── Update Banner (hidden) ──
        self.update_banner = QLabel("🚀 Nova versão disponível!")
        self.update_banner.setStyleSheet(
            "background-color: #8CC63F; color: #FFFFFF; padding: 10px; font-weight: bold;"
        )
        self.update_banner.setAlignment(Qt.AlignCenter)
        self.update_banner.hide()
        main_layout.addWidget(self.update_banner)

        # ── Content ──
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Card: Config
        config_frame = QFrame()
        config_frame.setObjectName("containerFrame")
        card_layout = QVBoxLayout(config_frame)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)

        # File Row
        file_row = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("Selecione o arquivo de dados (.xlsx, .csv)...")
        self.file_path_input.setReadOnly(True)
        btn_file = QPushButton("📂 Selecionar Arquivo")
        btn_file.clicked.connect(self.select_file)
        file_row.addWidget(self.file_path_input)
        file_row.addWidget(btn_file)
        card_layout.addLayout(file_row)

        # Company selection row
        company_row = QHBoxLayout()
        company_row.addWidget(QLabel("Empresa:"))
        self.combo_company = QComboBox()
        self.combo_company.addItem("Todas (Processar tudo)")
        self.combo_company.setMinimumWidth(300)
        company_row.addWidget(self.combo_company, 1)
        card_layout.addLayout(company_row)

        # Options Row
        opts_row = QHBoxLayout()

        # Model
        mdl_col = QVBoxLayout()
        mdl_col.addWidget(QLabel("Modelo Gemini:"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(["gemini-3-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"])
        self.combo_model.setCurrentText("gemini-3-pro-preview")
        mdl_col.addWidget(self.combo_model)
        opts_row.addLayout(mdl_col)

        # Analysis Type (loaded from prompts/ folder)
        type_col = QVBoxLayout()
        type_col.addWidget(QLabel("Tipo de Análise:"))
        self.combo_prompt_type = QComboBox()
        self.combo_prompt_type.addItem("-- Selecione um prompt --")
        type_col.addWidget(self.combo_prompt_type)
        opts_row.addLayout(type_col)

        card_layout.addLayout(opts_row)
        content_layout.addWidget(config_frame)

        # Start Button
        self.btn_process = QPushButton("▶  Iniciar Processamento")
        self.btn_process.setObjectName("btnStart")
        self.btn_process.setFixedHeight(50)
        self.btn_process.clicked.connect(self.start_processing)
        content_layout.addWidget(self.btn_process)

        # Logs
        content_layout.addWidget(QLabel("Logs de Execução:"))
        self.log_area = QTextEdit()
        self.log_area.setObjectName("logArea")
        self.log_area.setReadOnly(True)
        content_layout.addWidget(self.log_area)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        content_layout.addWidget(self.progress_bar)

        main_layout.addWidget(content, 1)

        # ── Status Bar (Footer) ──
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Gear button on the LEFT of the status bar
        btn_gear = QPushButton("  ⚙ Configurações  ")
        btn_gear.setFixedHeight(24)
        btn_gear.setStyleSheet(
            "QPushButton { background: #E2E8F0; border: 1px solid #CBD5E1; border-radius: 4px; "
            "font-size: 13px; color: #475569; padding: 2px 10px; }"
            "QPushButton:hover { background: #2BA8A0; color: white; border-color: #2BA8A0; }"
        )
        btn_gear.setToolTip("Abrir Configurações")
        btn_gear.clicked.connect(self.open_settings)
        self.status_bar.addWidget(btn_gear)

        # Status label on the RIGHT
        self.lbl_status = QLabel("Inicializando...")
        self.status_bar.addPermanentWidget(self.lbl_status)

    # ── Prompt Loading ──

    def load_prompts_from_disk(self):
        """Load .md prompt files from prompts/ into combo box."""
        prompts_dir = os.path.join(self.project_root, 'prompts')
        try:
            files = sorted([f for f in os.listdir(prompts_dir) if f.endswith('.md')])
            if files:
                for f in files:
                    name = os.path.splitext(f)[0]
                    self.combo_prompt_type.addItem(name)
                self.log(f"{len(files)} prompts carregados de disco.", "success")
        except Exception as e:
            self.log(f"Erro ao listar prompts: {e}", "error")

    # ── Version & Connectivity ──

    def check_local_version(self):
        try:
            with open(os.path.join(self.updater.base_dir, 'version.json'), 'r', encoding='utf-8') as f:
                v_data = json.load(f)
                self.local_version = v_data.get('version', 'Unknown')
                self.update_status_footer("ready")
        except:
            self.local_version = "Unknown"
            self.update_status_footer("error")

    def check_remote_version(self):
        try:
            has_update, new_v = self.updater.check_for_updates()
            if has_update:
                version_str = new_v.get('version', '?') if isinstance(new_v, dict) else str(new_v)
                self.update_banner.setText(f"🚀 Nova versão disponível ({version_str})! Reinicie para aplicar.")
                self.update_banner.show()
        except Exception as e:
            print(f"Update check failed: {e}")

    def check_github_connectivity(self):
        try:
            url = "https://raw.githubusercontent.com/andreocc/XALQ-Agent/main/version.json"
            headers = {}
            pat = self.worker_engine.github_pat
            if pat:
                headers["Authorization"] = f"token {pat}"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                self.github_connected = True
                self.update_status_footer("connected")
                self.log("GitHub conectado com sucesso.", "success")
            else:
                self.github_connected = False
                self.update_status_footer("offline")
                self.log(f"GitHub retornou status {resp.status_code}.", "error")
        except Exception as e:
            self.github_connected = False
            self.update_status_footer("offline")
            self.log(f"GitHub offline: {e}", "error")

    def update_status_footer(self, state):
        v = self.local_version
        if state == "connected":
            self.lbl_status.setText(f"🟢 Conectado: XALQ v{v}")
            self.lbl_status.setStyleSheet("color: #16a34a;")
        elif state == "offline":
            self.lbl_status.setText("🔴 Offline / Erro de Auth")
            self.lbl_status.setStyleSheet("color: #dc2626;")
        elif state == "processing":
            model = self.combo_model.currentText()
            self.lbl_status.setText(f"🧠 Processando via: {model}")
            self.lbl_status.setStyleSheet("color: #2BA8A0;")
        elif state == "ready":
            self.lbl_status.setText(f"XALQ v{v} | Status: Pronto")
            self.lbl_status.setStyleSheet("color: #64748B;")
        elif state == "done":
            self.lbl_status.setText(f"🟢 XALQ v{v} | Concluído")
            self.lbl_status.setStyleSheet("color: #16a34a;")
        elif state == "error":
            self.lbl_status.setText(f"🔴 XALQ v{v} | Erro")
            self.lbl_status.setStyleSheet("color: #dc2626;")

    # ── Actions ──

    def refresh_models(self):
        try:
            if hasattr(self, 'worker_engine'):
                real = self.worker_engine.get_available_models()
                if real:
                    current = self.combo_model.currentText()
                    self.combo_model.clear()
                    self.combo_model.addItems(real)
                    idx = self.combo_model.findText(current)
                    if idx >= 0:
                        self.combo_model.setCurrentIndex(idx)
                    else:
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
            # Populate company combo
            self.combo_company.clear()
            self.combo_company.addItem("Todas (Processar tudo)")
            try:
                df, items = self.worker_engine.load_data(f)
                if items:
                    for item in items:
                        self.combo_company.addItem(item)
                    self.log(f"{len(items)} empresas encontradas.", "success")
            except Exception as e:
                self.log(f"Erro ao listar empresas: {e}", "error")

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
        self.worker_engine = WorkerEngine(progress_callback=self.update_log_from_worker)

    def start_processing(self):
        file_path = self.file_path_input.text()
        if not file_path:
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo primeiro.")
            return

        model = self.combo_model.currentText()
        prompt_type = self.combo_prompt_type.currentText()
        if "Selecione" in prompt_type:
            QMessageBox.warning(self, "Aviso", "Selecione um tipo de análise (prompt) antes de processar.")
            return

        # Company selection -> rows_to_process
        rows_to_process = None
        company_sel = self.combo_company.currentText()
        if "Todas" not in company_sel:
            try:
                row_idx = int(company_sel.split(":")[0].strip())
                rows_to_process = [row_idx]
            except ValueError:
                pass

        self.btn_process.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.update_status_footer("processing")

        self.processing_thread = QThread()
        self.worker = ProcessingWorker(file_path, model, rows_to_process, prompt_type_override=prompt_type)
        self.worker.moveToThread(self.processing_thread)

        self.processing_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.progress.connect(self.update_log_from_worker)
        self.worker.error.connect(self.on_processing_error)

        self.processing_thread.start()

    def on_processing_finished(self):
        self.btn_process.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.update_status_footer("done")
        self.log("Processamento finalizado com sucesso.", "success")

        try:
            os.startfile(self.worker_engine.output_dir)
        except:
            pass

        if self.processing_thread:
            self.processing_thread.quit()
            self.processing_thread.wait()

    def on_processing_error(self, err_msg):
        self.btn_process.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.update_status_footer("error")
        self.log(f"Erro: {err_msg}", "error")
        if self.processing_thread:
            self.processing_thread.quit()
            self.processing_thread.wait()

    # ── Logging ──

    def update_log_from_worker(self, msg):
        level = "info"
        if "erro" in msg.lower() or "falha" in msg.lower():
            level = "error"
        elif "sucesso" in msg.lower() or "gerado" in msg.lower():
            level = "success"
        elif "---" in msg:
            level = "highlight"
        self.log(msg, level)

    def log(self, message, level="info"):
        color = "#8CC63F"
        if level == "error":
            color = "#EF4444"
        elif level == "success":
            color = "#34D399"
        elif level == "highlight":
            color = "#60A5FA"
        elif level == "debug":
            color = "#94A3B8"

        html = f'<span style="color:{color};">{message}</span>'
        self.log_area.append(html)
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Cleanup ──

    def closeEvent(self, event):
        if hasattr(self, 'resource_monitor'):
            self.resource_monitor.close()
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.quit()
            self.processing_thread.wait(2000)
        super().closeEvent(event)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
