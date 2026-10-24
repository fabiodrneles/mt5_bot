"""Caminhos da pasta de dados do usuario (spec 003 FR-1).

Fonte unica para onde o MT5Bot grava trades, estado, logs e o config.toml:
  Windows: %APPDATA%\\mt5bot
  macOS:   ~/Library/Application Support/mt5bot
  Linux:   $XDG_DATA_HOME/mt5bot (padrao ~/.local/share/mt5bot)
A variavel MT5BOT_DATA_DIR sobrepoe tudo (usada nos testes e em instalacoes
portateis). Se ja existir a pasta antiga ~/.mt5bot, ela continua sendo usada.
"""
import os
import sys


def data_dir() -> str:
    override = os.getenv("MT5BOT_DATA_DIR")
    if override:
        base = override
    elif sys.platform == "win32":
        base = os.path.join(os.getenv("APPDATA") or os.getenv("LOCALAPPDATA") or os.path.expanduser("~"), "mt5bot")
    else:
        legacy = os.path.join(os.path.expanduser("~"), ".mt5bot")
        if os.path.isdir(legacy):
            base = legacy
        elif sys.platform == "darwin":
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "mt5bot")
        else:
            base = os.path.join(os.getenv("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share"),
                                "mt5bot")
    os.makedirs(base, exist_ok=True)
    return base


def data_file(name: str) -> str:
    return os.path.join(data_dir(), name)


def logs_dir() -> str:
    path = os.path.join(data_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path


def config_file() -> str:
    return data_file("config.toml")
