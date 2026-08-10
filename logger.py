import logging
import os
from datetime import datetime
import config


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


_bot_logger = setup_logger()


def info(msg, **kwargs):
    _bot_logger.info(msg, **kwargs)


def warning(msg, **kwargs):
    _bot_logger.warning(msg, **kwargs)


def error(msg, **kwargs):
    _bot_logger.error(msg, **kwargs)


def debug(msg, **kwargs):
    _bot_logger.debug(msg, **kwargs)