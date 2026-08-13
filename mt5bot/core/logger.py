import logging
import os
from datetime import datetime
from mt5bot.core import config


def setup_logger():
    logger = logging.getLogger("mt5_bot")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # Console handler (sempre funciona)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.LOG_LEVEL)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
    )
    logger.addHandler(console_handler)

    # File handler (com protecao contra permissoes)
    try:
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, f"bot_{datetime.now().strftime('%Y%m%d')}.log")

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(file_handler)
    except (PermissionError, OSError):
        logger.warning("Nao foi possivel criar arquivo de log. Usando apenas console.")

    return logger


import threading
import urllib.request
import urllib.error
import json
import os
from mt5bot.core import config

def send_telegram_alert_async(message: str, level: str):
    """Envia alerta via Telegram em background sem travar o bot (Fire and Forget)."""
    token = getattr(config, "TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN"))
    chat_id = getattr(config, "TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID"))
    
    if not token or not chat_id:
        return
        
    def _send():
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            prefix = "⚠️ [AVISO]" if level == "WARNING" else "🛑 [ERRO CRÍTICO]"
            data = {
                "chat_id": chat_id,
                "text": f"{prefix}\n{message}"
            }
            req = urllib.request.Request(
                url, 
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            urllib.request.urlopen(req, timeout=3.0)
        except Exception:
            pass # Falha silenciosa

    # Dispara a thread sem aguardar retorno
    t = threading.Thread(target=_send, daemon=True)
    t.start()


_bot_logger = setup_logger()


def info(msg, **kwargs):
    _bot_logger.info(msg, **kwargs)


def warning(msg, **kwargs):
    _bot_logger.warning(msg, **kwargs)
    send_telegram_alert_async(msg, "WARNING")


def error(msg, **kwargs):
    _bot_logger.error(msg, **kwargs)
    send_telegram_alert_async(msg, "ERROR")


def debug(msg, **kwargs):
    _bot_logger.debug(msg, **kwargs)