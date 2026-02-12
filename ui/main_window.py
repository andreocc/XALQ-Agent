import sys
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QLineEdit, QFileDialog, 
                               QListWidget, QListWidgetItem, QProgressBar, QMessageBox,
                               QComboBox, QFrame)
from PySide6.QtCore import Qt, QThread, QSize, QSettings, QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QAction

from core.processing_worker import ProcessingWorker
from core.worker_engine import WorkerEngine
from ui.settings_dialog import SettingsDialog
from ui.resource_monitor import ResourceMonitor

from core.updater import Updater

class UpdateWorker(QObject):
    finished = Signal(bool, dict) # update_available, remote_data
    
    def __init__(self, updater):
        super().__init__()
        self.updater = updater

    def run(self):
        is_update, data = self.updater.check_for_updates()
        self.finished.emit(is_update, data)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.updater = Updater()
        local_ver = self.updater.get_local_version().get("version", "?.?.?")
        self.setWindowTitle(f"XALQ Agent v{local_ver} - Processador de Relatórios")
        self.setGeometry(100, 100, 800, 700)
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. Logo Section
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self._load_logo()
        main_layout.addWidget(self.logo_label)

        # 1.1 Resource Monitor (New)
        res_layout = QHBoxLayout()
        res_layout.addStretch()
        self.lbl_cpu = QLabel("CPU: -%")
        self.lbl_cpu.setStyleSheet("font-size: 10px; color: #666; margin-right: 10px;")
        res_layout.addWidget(self.lbl_cpu)
        
        self.lbl_ram = QLabel("RAM: -%")
        self.lbl_ram.setStyleSheet("font-size: 10px; color: #666;")
        res_layout.addWidget(self.lbl_ram)
        main_layout.addLayout(res_layout)

        # Start Monitor
        self.res_monitor = ResourceMonitor(self)
        self.res_monitor.usage_update.connect(self.update_resources)
        self.res_monitor.start()

        # 2. File Selection Section
        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Selecione o arquivo CSV ou XLSX para processar...")
        self.file_input.setReadOnly(True)
        file_layout.addWidget(self.file_input)

        self.btn_browse = QPushButton("📁 Escolher Arquivo")
        self.btn_browse.clicked.connect(self.browse_file)
        file_layout.addWidget(self.btn_browse)
        main_layout.addLayout(file_layout)

        # 2.1 Model Selection & Settings Section (New)
        model_layout = QHBoxLayout()
        
        model_layout.addWidget(QLabel("Modelo Gemini:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(150)
        model_layout.addWidget(self.model_combo)
        
        self.btn_refresh_models = QPushButton("🔄")
        self.btn_refresh_models.setToolTip("Atualizar lista de modelos")
        self.btn_refresh_models.setMaximumWidth(30)
        self.btn_refresh_models.clicked.connect(self.refresh_models)
        model_layout.addWidget(self.btn_refresh_models)

        # Spacer
        model_layout.addStretch()

        self.btn_settings = QPushButton("⚙ Configurar")
        self.btn_settings.clicked.connect(self.open_settings)
        model_layout.addWidget(self.btn_settings)

        main_layout.addLayout(model_layout)

        # 2.2 Prompt Type Selection (New)
        prompt_type_layout = QHBoxLayout()
        prompt_type_layout.addWidget(QLabel("Tipo de Análise:"))
        self.prompt_type_combo = QComboBox()
        self.prompt_type_combo.setMinimumWidth(200)
        prompt_type_layout.addWidget(self.prompt_type_combo)
        
        self.btn_refresh_prompts = QPushButton("🔄")
        self.btn_refresh_prompts.setToolTip("Atualizar lista de prompts")
        self.btn_refresh_prompts.setMaximumWidth(30)
        self.btn_refresh_prompts.clicked.connect(self.refresh_prompts)
        prompt_type_layout.addWidget(self.btn_refresh_prompts)

        prompt_type_layout.addStretch()
        main_layout.addLayout(prompt_type_layout)

        # 2.3 Company Selection (New)
        company_layout = QHBoxLayout()
        company_layout.addWidget(QLabel("Selecionar Empresa (Linha):"))
        self.company_combo = QComboBox()
        self.company_combo.addItem("Todas as Empresas (Processamento Completo)")
        self.company_combo.setEnabled(False)
        company_layout.addWidget(self.company_combo)
        main_layout.addLayout(company_layout)

        # 3. Action Buttons Section
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ Iniciar Processamento")
        self.btn_start.clicked.connect(self.start_processing)
        self.btn_start.setEnabled(False) 
        # Optional styling
        self.btn_start.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        
        btn_layout.addWidget(self.btn_start)
        main_layout.addLayout(btn_layout)

        # 4. Status Indicators
        self.status_label = QLabel("Aguardando arquivo...")
        self.status_label.setStyleSheet("font-weight: bold; color: #555;")
        main_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0) # Indeterminate initially
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 5. Timeline / Log
        lbl_timeline = QLabel("Progresso do Processamento:")
        lbl_timeline.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(lbl_timeline)
        
        self.timeline_list = QListWidget()
        main_layout.addWidget(self.timeline_list)

        # Internal State
        self.worker = None
        self.thread = None
        self.generated_files_cache = []
        
        # Settings persistence
        self.settings = QSettings("XALQ", "XALQ Agent")

        # Initializes models
        self.refresh_models()
        self.refresh_prompts()
        
        # Restore last used model
        self._restore_last_model()
        
        # Trigger update check (threaded)
        self._start_update_check()
    
    def _start_update_check(self):
        self.update_thread = QThread()
        self.update_worker = UpdateWorker(self.updater)
        self.update_worker.moveToThread(self.update_thread)
        
        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.finished.connect(self.handle_update_check)
        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.finished.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        
        self.update_thread.start()
        
    def handle_update_check(self, is_update, remote_data):
        if is_update:
            remote_ver = remote_data.get("version", "?")
            is_critical = remote_data.get("critical_update", False)
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Atualização Disponível")
            msg.setText(f"Uma nova versão ({remote_ver}) está disponível.")
            
            if is_critical:
                msg.setIcon(QMessageBox.Critical)
                msg.setInformativeText("Esta é uma atualização crítica. O sistema será atualizado automaticamente agora.")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()
                self._run_auto_update()
            else:
                msg.setIcon(QMessageBox.Question)
                msg.setInformativeText("Deseja atualizar agora?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.Yes)
                ret = msg.exec()
                
                if ret == QMessageBox.Yes:
                    self._run_auto_update()
        else:
            self.add_timeline_event("✅ Aplicação atualizada (v" + self.updater.get_local_version().get("version") + ")")

    def _run_auto_update(self):
        self.status_label.setText("Atualizando sistema...")
        self.progress_bar.setVisible(True)
        self.add_timeline_event("⬇️ Iniciando atualização via Git...", "process")
        
        success, message = self.updater.perform_update()
        
        self.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(self, "Sucesso", message)
            sys.exit(0)
        else:
            QMessageBox.critical(self, "Erro na Atualização", message)
            self.add_timeline_event(f"❌ {message}", "error")

    def _load_logo(self):
        # Resolve path relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Assuming structure: ui/main_window.py -> templates/img/0_XALQ-0.png
        # So we go up one level then into templates/img
        logo_path = os.path.join(current_dir, "..", "templates", "img", "0_XALQ-0.png")
        logo_path = os.path.normpath(logo_path)
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale if too large (760 is max width for 800px window with 20px margins)
            if pixmap.width() > 760:
                pixmap = pixmap.scaledToWidth(760, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText(f"[Logotipo não encontrado em: {logo_path}]")
            self.logo_label.setStyleSheet("color: red;")

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Selecionar Arquivo de Dados", 
            "", 
            "Arquivos Excel/CSV (*.xlsx *.xls *.csv);;Todos os Arquivos (*)"
        )
        if file_name:
            self.file_input.setText(file_name)
            self.status_label.setText("Carregando dados do arquivo...")
            self.add_timeline_event(f"📄 Arquivo selecionado: {os.path.basename(file_name)}")
            
            # Load company data
            engine = WorkerEngine()
            _, items = engine.load_data(file_name)
            
            self.company_combo.clear()
            self.company_combo.addItem("Todas as Empresas (Processamento Completo)")
            if items:
                self.company_combo.addItems(items)
                self.company_combo.setEnabled(True)
                self.add_timeline_event(f"📋 {len(items)} empresas identificadas.")
            else:
                self.company_combo.setEnabled(False)
                self.add_timeline_event("⚠️ Nenhuma empresa identificada ou erro ao ler arquivo.", "error")

            self.btn_start.setEnabled(True)
            self.status_label.setText("Arquivo carregado. Pronto para iniciar.")

    def refresh_models(self):
        engine = WorkerEngine()
        models = engine.get_available_models()
        self.model_combo.clear()
        if models:
            self.model_combo.addItems(models)
            self.status_label.setText(f"Modelos carregados: {len(models)}")
        else:
            self.model_combo.addItem("gemini-1.5-pro") # Default fallback
            self.status_label.setText("Usando modelos padrão.")
    
    def refresh_prompts(self):
        engine = WorkerEngine()
        prompts = engine.get_prompts_list()
        self.prompt_type_combo.clear()
        if prompts:
            self.prompt_type_combo.addItems(prompts)
            self.status_label.setText(f"Prompts carregados: {len(prompts)}")
        else:
            self.prompt_type_combo.addItem("revenue") # Fallback
            self.prompt_type_combo.addItem("operations") # Fallback
            self.status_label.setText("Nenhum prompt encontrado. Usando padrões.")
    
    def _restore_last_model(self):
        """Restore the last used model selection."""
        last_model = self.settings.value("last_model", "")
        if last_model:
            index = self.model_combo.findText(last_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
                self.add_timeline_event(f"🔄 Modelo anterior restaurado: {last_model}")
    
    def _save_last_model(self, model_name):
        """Save the currently selected model."""
        self.settings.setValue("last_model", model_name)
        self.settings.sync()

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def add_timeline_event(self, message, status_type="info"):
        item = QListWidgetItem(message)
        # Simple coloring/icon logic
        if "❌" in message or "erro" in message.lower() or status_type == "error":
            item.setForeground(Qt.red)
        elif "✅" in message or "sucess" in message.lower():
            item.setForeground(Qt.darkGreen)
        elif "⏳" in message or "processando" in message.lower():
            item.setForeground(Qt.blue)
        elif "📂" in message:
             item.setForeground(Qt.blue)
        
        self.timeline_list.addItem(item)
        self.timeline_list.scrollToBottom()

    def start_processing(self):
        file_path = self.file_input.text()
        if not file_path:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione um arquivo primeiro.")
            return
        
        selected_model = self.model_combo.currentText()
        
        # Save the selected model for next time
        self._save_last_model(selected_model)
        
        # Determine prompt type
        prompt_type = self.prompt_type_combo.currentText()
        
        # Determine rows to process
        rows_to_process = None
        if self.company_combo.currentIndex() > 0: # Not "Todas"
            # Format is "Index: Name", e.g. "1: Empresa X"
            selected_text = self.company_combo.currentText()
            try:
                idx_str = selected_text.split(':')[0]
                rows_to_process = [int(idx_str)]
            except:
                pass

        # Prepare UI
        self.btn_start.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.btn_settings.setEnabled(False) 
        self.company_combo.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Inicializando engine...")
        self.timeline_list.clear()
        self.add_timeline_event("🚀 Iniciando processamento...")
        if rows_to_process:
            self.add_timeline_event(f"🎯 Processando apenas a linha: {rows_to_process[0]}")
        self.add_timeline_event(f"🧠 Modelo selecionado: {selected_model}")
        self.add_timeline_event(f"📊 Tipo de análise: {self.prompt_type_combo.currentText()}")

        self.generated_files_cache = []

        # Setup Thread and Worker
        self.thread = QThread()
        self.worker = ProcessingWorker(
            file_path, 
            model_override=selected_model,
            rows_to_process=rows_to_process,
            prompt_type_override=prompt_type
        )
        self.worker.moveToThread(self.thread)

        # Connect Signals
        self.thread.started.connect(self.worker.run)
        
        # Worker signals -> UI slots
        self.worker.progress.connect(self.update_timeline)
        self.worker.status.connect(self.update_status)
        self.worker.error.connect(self.handle_error)
        self.worker.files_generated.connect(self.handle_files_generated)
        self.worker.finished.connect(self.process_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.cleanup_thread)

        # Start
        self.thread.start()

    def update_timeline(self, message):
        self.add_timeline_event(message)

    def update_status(self, message):
        self.status_label.setText(message)

    def handle_error(self, message):
        self.add_timeline_event(f"❌ Erro: {message}", "error")
        QMessageBox.critical(self, "Erro de Processamento", message)

    def handle_files_generated(self, files):
        self.generated_files_cache = files
        for f in files:
            self.add_timeline_event(f"📂 Arquivo gerado: {os.path.basename(f)}")

    def process_finished(self):
        try:
            self.status_label.setText("Processamento finalizado.")
            self.progress_bar.setVisible(False)
            self.btn_start.setEnabled(True)
            self.btn_browse.setEnabled(True)
            self.btn_settings.setEnabled(True)
            self.company_combo.setEnabled(True)
            self.add_timeline_event("🏁 Ciclo de execução terminado.")

            if self.generated_files_cache:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Processamento Concluído!")
                msg_box.setText("O processamento foi finalizado com sucesso.")
                msg_box.setInformativeText(f"{len(self.generated_files_cache)} relatórios foram gerados.\nO primeiro arquivo será aberto automaticamente.")
                msg_box.setIcon(QMessageBox.Information)
                msg_box.exec()

                # Auto-open first file
                try:
                    first_file = self.generated_files_cache[0]
                    if os.path.exists(first_file):
                        if sys.platform == 'win32':
                            os.startfile(first_file)
                        else:
                            import subprocess
                            opener = "open" if sys.platform == "darwin" else "xdg-open"
                            subprocess.call([opener, first_file])
                except Exception as e:
                    self.add_timeline_event(f"⚠️ Erro ao abrir arquivo automaticamente: {e}", "error")
        except Exception as e:
             self.add_timeline_event(f"❌ Erro na finalização da UI: {e}", "error")
             QMessageBox.critical(self, "Erro", f"Erro na finalização: {e}")

    def update_resources(self, cpu, ram):
        self.lbl_cpu.setText(f"CPU: {cpu:.1f}%")
        self.lbl_ram.setText(f"RAM: {ram:.1f}%")

    def cleanup_thread(self):
        self.thread = None
        self.worker = None
