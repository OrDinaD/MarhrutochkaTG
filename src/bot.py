#!/usr/bin/env python3
"""Совместимый модуль запуска Telegram-бота."""
from __future__ import annotations

from telegram.ext import ConversationHandler

from bot_app import application as _app
from bot_app import state as _state
from bot_app.application import (
    button_callback,
    handle_check_now,
    handle_text_input,
    main,
    stop_monitoring,
)
from bot_app.handlers import search as _search_module
from bot_app.handlers.search import perform_route_search as _perform_route_search
from bot_app.monitoring_service import format_monitor_config
from bot_app.parser import init_parser as _init_parser
from src.managers.user_manager import user_manager
from src.utils.telegram_safe import safe_answer_callback, safe_edit_message

# Совместимость со старыми тестами и кодом
parser = _state.parser
user_data_store = _state.user_data_store
active_monitors = _state.active_monitors
job_queue = _state.job_queue


async def init_parser():
    """Совместимый враппер инициализации парсера."""
    parser_instance = await _init_parser()
    global parser
    parser = parser_instance
    _state.parser = parser_instance
    return parser_instance


async def perform_route_search(query, user_id: int, from_city: str, to_city: str, date: str):
    """Совместимый враппер поиска маршрутов."""
    if parser is not None:
        async def _return_parser():
            return parser
        _search_module.init_parser = _return_parser
        _state.parser = parser
    else:
        _search_module.init_parser = init_parser
    return await _perform_route_search(query, user_id, from_city, to_city, date)


async def _safe_edit_message_proxy(*args, **kwargs):
    return await safe_edit_message(*args, **kwargs)


async def _safe_answer_callback_proxy(*args, **kwargs):
    return await safe_answer_callback(*args, **kwargs)


_app.safe_edit_message = _safe_edit_message_proxy
_app.safe_answer_callback = _safe_answer_callback_proxy
_search_module.safe_edit_message = _safe_edit_message_proxy
from bot_app.handlers import monitoring as _monitoring_module
_monitoring_module.safe_edit_message = _safe_edit_message_proxy
_monitoring_module.safe_answer_callback = _safe_answer_callback_proxy
from bot_app import callback_management as _callback_module
_callback_module.safe_answer_callback = _safe_answer_callback_proxy


__all__ = [
    "main",
    "handle_text_input",
    "button_callback",
    "stop_monitoring",
    "handle_check_now",
    "perform_route_search",
    "init_parser",
    "safe_edit_message",
    "safe_answer_callback",
    "format_monitor_config",
    "parser",
    "user_data_store",
    "active_monitors",
    "user_manager",
    "ConversationHandler",
    "job_queue",
]
