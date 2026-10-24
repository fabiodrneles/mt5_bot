"""Libera disco apagando o cache de historico do MT5 dos simbolos ja extraidos para a pesquisa.

Uso (com o MT5 FECHADO): python clean_mt5_cache.py [--dry-run]
So apaga a pasta bases/<servidor>/history/<SIMBOLO> de simbolos cujos arquivos de pesquisa ja existem
em data/ e que NAO sao rotas ao vivo (config.QUANT_ROUTES). O MT5 baixa de novo o que precisar.
Nao toca em conta, posicoes, configuracoes nem em outras pastas do terminal.
"""
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))


def mt5_running():
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    return "terminal64.exe" in out


def main():
    dry = "--dry-run" in sys.argv
    if mt5_running() and not dry:
        print("Feche o MT5 antes (os arquivos do cache ficam bloqueados enquanto ele roda).")
        return 1
    from mt5bot.core import config
    keep = set(config.QUANT_ROUTES)
    extracted = {os.path.basename(f).rsplit("_", 1)[0] for f in glob.glob(os.path.join(HERE, "data", "*_*.npy"))}
    root = os.path.join(os.environ.get("APPDATA", ""), "MetaQuotes", "Terminal")
    freed = removed = 0
    for hist in glob.glob(os.path.join(root, "*", "bases", "*", "history")):
        for sym_dir in glob.glob(os.path.join(hist, "*")):
            sym = os.path.basename(sym_dir)
            if sym in keep or sym not in extracted or not os.path.isdir(sym_dir):
                continue
            size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(sym_dir) for f in fs)
            if not dry:
                shutil.rmtree(sym_dir, ignore_errors=True)
            freed += size
            removed += 1
    verb = "seriam liberados" if dry else "liberados"
    print(f"{removed} simbolos, {freed / 1e9:.1f} GB {verb}. Mantidos (rotas ao vivo): {', '.join(sorted(keep))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
