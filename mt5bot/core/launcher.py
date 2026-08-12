import os
import subprocess
import sys
from datetime import datetime

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        try:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            with open(os.path.join(base, "pyproject.toml"), "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("version ="):
                        ver = line.split("=")[1].strip().strip('"')
                        print(f"MT5Bot v{ver}")
                        sys.exit(0)
        except Exception:
            pass
        print("MT5Bot v(desconhecida)")
        sys.exit(0)
        
    # Caminho do pacote atual: mt5bot/core/launcher.py
    # Então base_dir será mt5_bot-main
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    maestro_path = os.path.join(base_dir, "maestro", "maestro.exe")
    maestro_dir = os.path.dirname(maestro_path)
    
    # Auto-compile if .go files are newer than .exe
    needs_compile = not os.path.exists(maestro_path)
    if not needs_compile:
        try:
            exe_mtime = os.path.getmtime(maestro_path)
            for f in os.listdir(maestro_dir):
                if f.endswith(".go"):
                    go_file = os.path.join(maestro_dir, f)
                    if os.path.getmtime(go_file) > exe_mtime:
                        needs_compile = True
                        break
        except Exception:
            pass
            
    if needs_compile:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [CORE] Compilando maestro.exe...")
        try:
            subprocess.run(["go", "build", "-o", "maestro.exe"], cwd=maestro_dir, check=True)
        except Exception as e:
            print(f"Erro crítico: Falha ao compilar maestro.exe. {e}")
            sys.exit(1)
    
    if not os.path.exists(maestro_path):
        print(f"Erro crítico: Orquestrador Maestro não encontrado em {maestro_path}")
        sys.exit(1)
    
    # Executa o orquestrador Go
    os.chdir(maestro_dir)
    sys.exit(subprocess.call([maestro_path] + sys.argv[1:]))

if __name__ == "__main__":
    main()
