import sys
import os
import subprocess
import importlib.util

def install_dependencies():
    print("Verificando dependências...")
    requirements_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
    
    if not os.path.exists(requirements_file):
        print(f"[ERRO] Arquivo requirements.txt não encontrado em {requirements_file}")
        return False

    try:
        # Check core package
        import google.generativeai
        print("[OK] Dependências parecem estar instaladas.")
        return True
    except ImportError:
        print("[AVISO] Dependências faltantes. Instalando...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
            print("[SUCESSO] Dependências instaladas.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERRO] Falha ao instalar dependências: {e}")
            return False

def main():
    print("=== XALQ Agent Launcher ===")
    
    # 1. Check & Install Dependencies
    if not install_dependencies():
        print("\n[FALHA FATAL] Não foi possível configurar o ambiente.")
        input("Pressione Enter para sair...")
        sys.exit(1)

    # 2. Launch Main Application
    print("\nIniciando aplicação...")
    try:
        # Import main script logic or run it as subprocess
        # Running as subprocess is safer to ensure clean state
        main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Xalq.py')
        
        # Use subprocess to run Xalq.py so it runs in the (potentially new) environment
        result = subprocess.run([sys.executable, main_script], cwd=os.path.dirname(main_script))
        
        if result.returncode != 0:
            print(f"\n[ERRO] A aplicação encerrou com código {result.returncode}.")
            input("Pressione Enter para sair...")
            sys.exit(result.returncode)
            
    except Exception as e:
        print(f"\n[ERRO CRÍTICO] {e}")
        input("Pressione Enter para sair...")
        sys.exit(1)

if __name__ == "__main__":
    main()
