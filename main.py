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
    
    try:
        # Executa o Maestro em Go diretamente via go run
        # Nota: Go 1.20+ precisa estar instalado na máquina.
        subprocess.run(["go", "run", "."], cwd=maestro_dir)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print("ERRO CRITICO: Comando 'go' não encontrado no sistema.")
        print("A arquitetura Híbrida do MT5Bot requer o compilador Golang instalado.")
        print("Faça o download em: https://go.dev/dl/")
        sys.exit(1)

if __name__ == "__main__":
    main()