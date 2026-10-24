"""Todo modulo do pacote importa (spec 001 AC-2).

Pega imports quebrados e modulos faltando no pacote antes que cheguem ao
usuario: o MT5 e simulado pelo conftest, entao roda em Windows e Linux.
"""
import importlib
import pkgutil

import pytest

import mt5bot
import interfaces

MODULES = sorted(
    m.name for pkg in (mt5bot, interfaces)
    for m in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + ".")
)


def test_found_core_modules():
    for must in ("mt5bot.mentorship.supervisor", "mt5bot.execution.quant_manager",
                 "mt5bot.core.telemetry", "interfaces.dashboard", "interfaces.brain_worker"):
        assert must in MODULES


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)
