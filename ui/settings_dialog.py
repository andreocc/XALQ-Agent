from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPlainTextEdit, QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from core.worker_engine import WorkerEngine

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Prompts")
        self.resize(600, 500)
        
        # Helper engine just for reading/writing prompts
        self.engine = WorkerEngine()
        
        layout = QVBoxLayout(self)

        # Prompt Selection
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Editar Prompt:"))
        
        self.combo_prompts = QComboBox()
        self.combo_prompts.currentIndexChanged.connect(self.load_selected_prompt)
        header_layout.addWidget(self.combo_prompts)
        
        layout.addLayout(header_layout)

        # Editor
        self.editor = QPlainTextEdit()
        # Set a monospaced font
        font = self.editor.font()
        font.setFamily("Consolas") # Or "Monospace"
        font.setPointSize(10)
        self.editor.setFont(font)
        layout.addWidget(self.editor)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_refresh = QPushButton("🔄 Recarregar Lista")
        self.btn_refresh.clicked.connect(self.refresh_list)
        btn_layout.addWidget(self.btn_refresh)
        
        btn_layout.addStretch()
        
        self.btn_save = QPushButton("💾 Salvar Alterações")
        self.btn_save.clicked.connect(self.save_prompt)
        # Style the save button
        self.btn_save.setStyleSheet("font-weight: bold; background-color: #2e8b57; color: white;")
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)

        # Initial Load
        self.refresh_list()

    def refresh_list(self):
        prompts = self.engine.get_prompts_list()
        self.combo_prompts.blockSignals(True)
        self.combo_prompts.clear()
        self.combo_prompts.addItems(prompts)
        self.combo_prompts.blockSignals(False)
        
        if prompts:
            self.load_selected_prompt()
        else:
            self.editor.setPlainText("")
            self.editor.setPlaceholderText("Nenhum arquivo .md encontrado na pasta prompts/")

    def load_selected_prompt(self):
        filename = self.combo_prompts.currentText()
        if not filename: return
        
        content = self.engine.read_prompt_content(filename)
        if content is not None:
            self.editor.setPlainText(content)
        else:
            self.editor.setPlainText(f"Erro ao ler arquivo: {filename}")

    def save_prompt(self):
        filename = self.combo_prompts.currentText()
        if not filename: return

        content = self.editor.toPlainText()
        success = self.engine.save_prompt_content(filename, content)
        
        if success:
            QMessageBox.information(self, "Sucesso", f"Prompt '{filename}' salvo com sucesso!")
        else:
            QMessageBox.critical(self, "Erro", "Falha ao salvar o arquivo. Verifique os logs.")
