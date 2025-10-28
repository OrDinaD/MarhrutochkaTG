"""Глобальное состояние Telegram-бота."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

# Директория для хранения данных
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

from src.managers.user_manager import user_manager

# Глобальные состояния, которые используются различными модулями бота
parser: Optional[Any] = None
job_queue: Optional[Any] = None
application: Optional[Any] = None
admin_panel: Optional[Any] = None
user_data_store = user_manager.user_data_store
active_monitors = user_manager.active_monitors

# Отслеживание callback-хендлеров
active_callbacks: Dict[int, Dict[str, Any]] = {}
callback_timeout_seconds: int = 45

# Названия фоновых задач
CLEANUP_JOB_NAME = "cleanup_stuck_callbacks"
RESTART_JOB_NAME = "admin_restart_bot"

__all__ = [
    "DATA_DIR",
    "parser",
    "job_queue",
    "application",
    "admin_panel",
    "user_data_store",
    "active_monitors",
    "active_callbacks",
    "callback_timeout_seconds",
    "CLEANUP_JOB_NAME",
    "RESTART_JOB_NAME",
]
