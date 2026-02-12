import sys
import traceback
from PySide6.QtCore import QObject, Signal, QThread
from core.worker_engine import WorkerEngine

class ProcessingWorker(QObject):
    """
    Worker que executa o processamento em uma thread separada.
    """
    finished = Signal()
    error = Signal(str)
    progress = Signal(str)
    status = Signal(str)

    files_generated = Signal(list)

    def __init__(self, file_path, model_override=None, rows_to_process=None, prompt_type_override=None):
        super().__init__()
        self.file_path = file_path
        self.model_override = model_override
        self.rows_to_process = rows_to_process
        self.prompt_type_override = prompt_type_override
        self._is_running = True

    def run(self):
        try:
            # Callback bridge: WorkerEngine -> UI Signals
            def bridge_callback(message):
                if not self._is_running:
                    return
                # Heurística simples para categorizar mensagens
                if "ERRO" in message.upper() or "ERROR" in message.upper():
                    self.error.emit(message)
                elif "Processando linha" in message:
                    self.status.emit(message) # Atualiza o status principal
                    self.progress.emit(message) # Adiciona na timeline
                elif "concluído" in message.lower():
                    self.progress.emit(f"✅ {message}")
                elif "iniciando" in message.lower():
                    self.progress.emit(f"🚀 {message}")
                else:
                    self.progress.emit(message)

            engine = WorkerEngine(progress_callback=bridge_callback)
            # Returns list of generated files
            generated_files = engine.process_file(
                self.file_path, 
                model_override=self.model_override,
                rows_to_process=self.rows_to_process,
                prompt_type_override=self.prompt_type_override
            )

            if generated_files:
                self.files_generated.emit(generated_files)
                self.progress.emit("🏁 Processamento finalizado com sucesso!")
            else:
                self.error.emit("Processamento finalizado sem gerar arquivos (ou com erros).")

        except Exception as e:
            self.error.emit(f"Erro crítico: {str(e)}")
            traceback.print_exc()
        finally:
            self.finished.emit()

    def stop(self):
        self._is_running = False
