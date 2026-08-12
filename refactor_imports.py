
import os
import re

directories = ["mt5bot", "interfaces", "tests"]
modules = ["config", "executor", "indicators", "logger", "persistence", "risk_calculator", "tracker", "dashboard", "_preview_dashboard", "strategy", "scoring", "trailing", "execution_manager", "paper_tracker", "shutdown_manager"]

replacements = {
    r"import config": r"from mt5bot.core import config",
    r"from config import": r"from mt5bot.core.config import",
    r"import logger": r"from mt5bot.core import logger",
    r"from logger import": r"from mt5bot.core.logger import",
    r"import executor": r"from mt5bot.execution import executor",
    r"from executor import": r"from mt5bot.execution.executor import",
    r"import persistence": r"from mt5bot.data import persistence",
    r"from persistence import": r"from mt5bot.data.persistence import",
    r"import tracker": r"from mt5bot.data import tracker",
    r"from tracker import": r"from mt5bot.data.tracker import",
    r"import risk_calculator": r"from mt5bot.risk import risk_calculator",
    r"from risk_calculator import": r"from mt5bot.risk.risk_calculator import",
    r"import indicators": r"from mt5bot.engine import indicators",
    r"from indicators import": r"from mt5bot.engine.indicators import",
    
    # Brain replacements
    r"from brain.setups import": r"from mt5bot.engine.strategy import",
    r"import brain.setups": r"import mt5bot.engine.strategy",
    r"from brain.indicators import": r"from mt5bot.engine.indicators import",
    r"import brain.indicators": r"import mt5bot.engine.indicators",
    r"from brain.scoring import": r"from mt5bot.engine.scoring import",
    r"import brain.scoring": r"import mt5bot.engine.scoring",
    r"from brain.trailing import": r"from mt5bot.engine.trailing import",
    r"import brain.trailing": r"import mt5bot.engine.trailing",
    r"from brain.execution_manager import": r"from mt5bot.execution.execution_manager import",
    r"import brain.execution_manager": r"import mt5bot.execution.execution_manager",
    r"from brain.paper_tracker import": r"from mt5bot.data.paper_tracker import",
    r"import brain.paper_tracker": r"import mt5bot.data.paper_tracker",
    r"from brain.shutdown_manager import": r"from mt5bot.core.shutdown_manager import",
    r"import brain.shutdown_manager": r"import mt5bot.core.shutdown_manager",
    
    # General brain imports
    r"from brain import": r"from mt5bot import",
    r"import brain": r"import mt5bot"
}

for d in directories:
    for root, _, files in os.walk(d):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                new_content = content
                for old, new in replacements.items():
                    # We use simple string replace for speed, it should work for standard imports
                    new_content = new_content.replace(old, new)
                
                if new_content != content:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"Updated {path}")
print("Done")

