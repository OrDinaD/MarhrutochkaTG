"""Утилиты логирования для Telegram-бота."""
import logging
from typing import Any, Dict, Optional

from src.monitoring import setup_logging, railway_logger


if railway_logger:
    logger = railway_logger
else:
    logger = setup_logging(logging.INFO)


def safe_log(message: str, log_type: str = "system", data: Optional[Dict[str, Any]] = None, level: str = "info") -> None:
    """Безопасно записывает сообщение в лог, поддерживая кастомный логгер Railway."""
    emojis = {"system": "⚙️", "bot": "🤖", "admin": "👨‍💻"}
    method_name = f"{log_type}_action"

    if hasattr(logger, method_name):
        getattr(logger, method_name)(message, data or {}, level=level)
        return

    emoji = emojis.get(log_type, "ℹ️")
    getattr(logger, level, logger.info)(f"{emoji} {message}")


def safe_log_system(message: str, data: Optional[Dict[str, Any]] = None, level: str = "info") -> None:
    """Обертка для логирования системных сообщений."""
    safe_log(message, "system", data, level)


def safe_log_bot(message: str, data: Optional[Dict[str, Any]] = None, level: str = "info") -> None:
    """Обертка для логирования сообщений бота."""
    safe_log(message, "bot", data, level)


def safe_log_admin(message: str, data: Optional[Dict[str, Any]] = None, level: str = "info") -> None:
    """Обертка для логирования сообщений админ-панели."""
    safe_log(message, "admin", data, level)


__all__ = [
    "logger",
    "safe_log",
    "safe_log_system",
    "safe_log_bot",
    "safe_log_admin",
]
