"""Conexao com o terminal MetaTrader 5 (fonte unica para todos os pontos de entrada).

Com varias corretoras instaladas (ex.: Hantec e Clear, cada uma com o seu terminal), o robo precisa saber
a qual terminal se conectar. Sem configuracao, a biblioteca MetaTrader5 usa o ultimo terminal aberto.
Com `mt5_path = "C:/.../terminal64.exe"` no config.toml, ela abre exatamente esse terminal, e o login
salvo nele, sem deslogar os outros.
"""
import MetaTrader5 as mt5

from mt5bot.core import config


def initialize(**kwargs) -> bool:
    path = getattr(config, "MT5_PATH", None)
    return bool(mt5.initialize(path, **kwargs) if path else mt5.initialize(**kwargs))
