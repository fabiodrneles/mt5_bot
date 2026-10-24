"""Os modelos XGBoost versionados sao encontrados pelo supervisor (spec 004).

Mover os modelos sem ajustar o caminho desligaria o filtro de IA em silencio.
"""
import os

from mt5bot.mentorship.ml_xgboost import MLSupervisor


def test_supervisor_finds_versioned_models():
    for symbol in ("HK50", "JP225"):
        path = os.path.join(MLSupervisor._base_dir, f"mt5bot_xgboost_{symbol}_v2.json")
        assert os.path.exists(path), path
