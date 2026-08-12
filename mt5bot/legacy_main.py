import subprocess
import os
import sys

def main():
    """
    Novo Ponto de Entrada Global do MT5Bot Maestro.
    Este arquivo substitui o velho monólito em Python.
    Ao digitar 'mt5bot', este script roteia silenciosamente a execução
    para a arquitetura super rápida em Golang.
    """
    print("Iniciando o MT5Bot Maestro (Arquitetura Hibrida Go/Python)...")
    
    maestro_dir = os.path.join(os.path.dirname(__file__), "maestro")
    
    # Se não encontrar junto ao arquivo (ex: pip install normal), tenta no diretório atual
    if not os.path.isdir(maestro_dir):
        maestro_dir = os.path.join(os.getcwd(), "maestro")

    if not os.path.isdir(maestro_dir):
        print("ERRO CRITICO: Diretório 'maestro' não encontrado.")
        print("Se você instalou o bot via pip, utilize o modo de desenvolvimento:")
        print("    pip install -e .")
        print("Ou certifique-se de executar o comando a partir da raiz do projeto.")
        sys.exit(1)
    
    try:
        maestro_exe = os.path.join(maestro_dir, "maestro.exe")
        
        # Build se não existir
        if not os.path.exists(maestro_exe):
            print("Compilando motor Go pela primeira vez...")
            subprocess.run(["go", "build", "-o", "maestro.exe"], cwd=maestro_dir, check=True)
            
        # Troca o diretorio atual e chama o executavel diretamente
        # Isso evita que o "go run" interfira no modo do console (duplicando caracteres)
        os.chdir(maestro_dir)
        os.system("maestro.exe")
        
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print("ERRO CRITICO: Comando 'go' não encontrado no sistema.")
        print("A arquitetura Híbrida do MT5Bot requer o compilador Golang instalado.")
        print("Faça o download em: https://go.dev/dl/")
        sys.exit(1)

if __name__ == "__main__":
    main()