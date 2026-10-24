"""Verifica o pacote Python de verdade (spec 002 FR-1, AC-1).

Constroi o wheel, instala num venv limpo e importa TODOS os modulos de
`mt5bot` e `interfaces` a partir do pacote instalado (rodando fora do
repositorio, para nao usar o codigo-fonte por engano).

Uso:  python tools/check_wheel.py            (precisa de: pip install build)
Saida: codigo 0 se tudo importa; 1 com a lista de modulos quebrados.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IMPORT_ALL = r"""
import importlib, pkgutil, sys
import mt5bot, interfaces
assert "site-packages" in mt5bot.__file__.replace("\\", "/"), mt5bot.__file__
names = sorted(m.name for p in (mt5bot, interfaces)
               for m in pkgutil.walk_packages(p.__path__, prefix=p.__name__ + "."))
bad = []
for n in names:
    try:
        importlib.import_module(n)
    except Exception as e:
        bad.append(f"{n}: {type(e).__name__}: {e}")
print(f"{len(names)} modulos, {len(bad)} com erro")
for b in bad:
    print("  -", b)
stray = [m.name for m in pkgutil.iter_modules() if m.name in ("config", "strategy", "tracker", "tui", "executor")]
if stray:
    print("modulos soltos no topo do site-packages:", stray)
sys.exit(1 if bad or stray else 0)
"""


def run(cmd, **kw):
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def main():
    work = tempfile.mkdtemp(prefix="mt5bot-wheel-")
    try:
        dist = os.path.join(work, "dist")
        # build/ antigo contaminava o wheel com modulos velhos.
        shutil.rmtree(os.path.join(ROOT, "build"), ignore_errors=True)
        run([sys.executable, "-m", "build", "--wheel", "--outdir", dist, ROOT])
        wheel = glob.glob(os.path.join(dist, "*.whl"))[0]
        venv = os.path.join(work, "venv")
        run([sys.executable, "-m", "venv", venv])
        py = os.path.join(venv, "Scripts" if os.name == "nt" else "bin", "python")
        run([py, "-m", "pip", "install", "-q", wheel])
        result = subprocess.run([py, "-c", IMPORT_ALL], cwd=work)
        return result.returncode
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
