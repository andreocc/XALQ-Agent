import argparse
import os
from core.worker_engine import WorkerEngine

def main():
    parser = argparse.ArgumentParser(description="XALQ Agent CLI - Processador de Relatórios")
    parser.add_argument("file_path", type=str, help="Caminho para o arquivo CSV ou XLSX.")
    args = parser.parse_args()

    # Use a simple print callback for CLI
    def cli_callback(message):
        print(f"[PROGRESS] {message}")

    engine = WorkerEngine(progress_callback=cli_callback)
    
    if os.path.exists(args.file_path):
        success = engine.process_file(args.file_path)
        if success:
            print("\nProcessamento concluído com sucesso.")
        else:
            print("\nErro durante o processamento. Verifique os logs.")
    else:
        print(f"Erro: Arquivo não encontrado: {args.file_path}")

if __name__ == "__main__":
    main()
