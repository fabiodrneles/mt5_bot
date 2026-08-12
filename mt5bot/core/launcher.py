import os
import subprocess
import sys

def main():
    # Caminho do pacote atual: mt5bot/core/launcher.py
    # Então base_dir será mt5_bot-main
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    maestro_path = os.path.join(base_dir, "maestro", "maestro.exe")
    
    if not os.path.exists(maestro_path):
        print(f"Erro crítico: Orquestrador Maestro não encontrado em {maestro_path}")
        print("Certifique-se de que o maestro.exe foi compilado corretamente.")
        sys.exit(1)
    
    # Executa o orquestrador Go
    os.chdir(os.path.dirname(maestro_path))
    sys.exit(subprocess.call([maestro_path] + sys.argv[1:]))

if __name__ == "__main__":
    main()
