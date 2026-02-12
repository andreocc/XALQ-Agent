from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPlainTextEdit, QPushButton, QMessageBox, QLineEdit)
from PySide6.QtCore import Qt, QSettings
from core.worker_engine import WorkerEngine

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações do XALQ Agent")
        self.setMinimumSize(600, 500)
        self.engine = WorkerEngine()
        
        layout = QVBoxLayout(self)
        
        # Header / Selector
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Selecionar Prompt para Editar:"))
        
        self.prompt_combo = QComboBox()
        self.prompt_combo.addItems(self.engine.get_prompts_list())
        self.prompt_combo.currentTextChanged.connect(self.load_prompt)
        header_layout.addWidget(self.prompt_combo)
        
        layout.addLayout(header_layout)

        # API Keys Section
        keys_layout = QVBoxLayout()
        
        # Gemini API Key
        keys_layout.addWidget(QLabel("Gemini API Key:"))
        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setEchoMode(QLineEdit.Password)
        self.gemini_key_input.setPlaceholderText("Cole sua API Key do Google AI Studio aqui")
        keys_layout.addWidget(self.gemini_key_input)
        
        # GitHub PAT
        keys_layout.addWidget(QLabel("GitHub Personal Access Token (PAT):"))
        self.github_pat_input = QLineEdit()
        self.github_pat_input.setEchoMode(QLineEdit.Password)
        self.github_pat_input.setPlaceholderText("Cole seu GitHub PAT aqui (para acesso a prompts privados/rate limits)")
        keys_layout.addWidget(self.github_pat_input)
        
        layout.addLayout(keys_layout)
        
        # Load existing keys
        settings = QSettings("XALQ", "XALQ Agent")
        
        # Defaults provided by user request
        default_gemini = "AIzaSyA1R5VwkRUrdiSd4KQMEsCdEKQZ-blzWxk"
        default_github = "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"
        
        current_gemini = settings.value("gemini_api_key", "")
        if not current_gemini: current_gemini = default_gemini
            
        current_github = settings.value("github_pat", "")
        if not current_github: current_github = default_github
            
        self.gemini_key_input.setText(current_gemini)
        self.github_pat_input.setText(current_github)

        # Editor
        self.editor = QPlainTextEdit()
        # Set a monospaced font
        font = self.editor.font()
        font.setFamily("Consolas")
        font.setPointSize(10)
        self.editor.setFont(font)
        layout.addWidget(self.editor)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("💾 Salvar Alterações")
        self.btn_save.clicked.connect(self.save_prompt)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_close = QPushButton("Fechar")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        # Initial Load
        self.load_prompt(self.prompt_combo.currentText())

    def load_prompt(self, filename):
        if not filename: return
        # Ensure extension
        if not filename.endswith('.md'):
            filename += '.md'
            
        content = self.engine.load_agent_prompt(filename.replace('.md', '')) # Helper usually takes name
        if not content:
             # Try direct read if not found via helper logic (e.g. new file)
             content = self.engine.read_prompt_content(filename)
             
        if content:
            self.editor.setPlainText(content)
        else:
            self.editor.setPlainText(f"Novo prompt: {filename}\nEscreva seu prompt aqui...")

    def save_prompt(self):
        filename = self.prompt_combo.currentText()
        if not filename: return
        
        if not filename.endswith('.md'):
            filename += '.md'

        content = self.editor.toPlainText()
        
        # Save Keys
        settings = QSettings("XALQ", "XALQ Agent")
        settings.setValue("gemini_api_key", self.gemini_key_input.text().strip())
        settings.setValue("github_pat", self.github_pat_input.text().strip())
        settings.sync()
        
        success = self.engine.save_prompt_content(filename, content)
        
        if success:
            QMessageBox.information(self, "Sucesso", "Prompt e configurações salvos com sucesso!")
            # Reload engine config just in case
            self.engine._configure_gemini()
        else:
            QMessageBox.critical(self, "Erro", "Falha ao salvar o prompt.")
