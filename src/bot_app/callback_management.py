"""Управление состоянием callback-хендлеров и защитный декоратор."""
from __future__ import annotations

import asyncio
import functools
from datetime import datetime
from typing import Callable, Optional

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from src.utils.telegram_safe import safe_answer_callback, safe_edit_message
from src.managers.user_manager import user_manager

from . import state
from .keyboards import get_main_menu_keyboard
from .logging_utils import logger


async def track_callback_start(user_id: int, query_id: str, handler_name: str) -> None:
    """Фиксирует начало работы callback-хендлера."""
    state.active_callbacks[user_id] = {
        "query_id": query_id,
        "start_time": datetime.now(),
        "handler": handler_name,
    }
    logger.info(f"🔄 [{user_id}] Начало callback: {handler_name} (ID: {query_id})")


async def track_callback_end(user_id: int) -> None:
    """Фиксирует завершение работы callback-хендлера."""
    callback_info = state.active_callbacks.pop(user_id, None)
    if not callback_info:
        return

    duration = (datetime.now() - callback_info["start_time"]).total_seconds()
    logger.info(f"✅ [{user_id}] Завершен callback: {callback_info['handler']} ({duration:.2f}s)")


async def cleanup_stuck_callbacks() -> None:
    """Удаляет зависшие callback-хендлеры из отслеживания."""
    current_time = datetime.now()
    stuck_users = []

    for user_id, callback_info in list(state.active_callbacks.items()):
        duration = (current_time - callback_info["start_time"]).total_seconds()
        if duration > state.callback_timeout_seconds:
            stuck_users.append(user_id)
            logger.warning(
                "⚠️ [%s] Застрявший callback: %s (%.2fs)",
                user_id,
                callback_info["handler"],
                duration,
            )

    for user_id in stuck_users:
        state.active_callbacks.pop(user_id, None)
        logger.info("🧹 [%s] Принудительная очистка застрявшего callback", user_id)


async def emergency_conversation_reset(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выполняет экстренный сброс состояния разговора для пользователя."""
    try:
        context.user_data.clear()
        user_manager.emergency_reset_user(user_id)
        state.active_callbacks.pop(user_id, None)
        logger.warning("🚨 [%s] Экстренный сброс состояния conversation", user_id)
    except Exception as exc:  # pragma: no cover - логирование ошибок
        logger.error("❌ [%s] Ошибка при экстренном сбросе: %s", user_id, exc)


def callback_handler_protection(timeout: int = 30) -> Callable:
    """Декоратор, защищающий callback-хендлеры от зависания."""

    def decorator(func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Optional[int]]):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            if not query or not query.data:
                return await func(update, context)

            user = getattr(update, 'effective_user', None)
            user_id = user.id if user else query.from_user.id
            handler_name = func.__name__

            try:
                if user_id in state.active_callbacks:
                    old_callback = state.active_callbacks[user_id]
                    duration = (datetime.now() - old_callback["start_time"]).total_seconds()
                    if duration > 10:
                        logger.warning(
                            "⚠️ [%s] Прерываем застрявший callback: %s",
                            user_id,
                            old_callback["handler"],
                        )
                        await emergency_conversation_reset(user_id, context)

                await track_callback_start(user_id, query.id, handler_name)
                await safe_answer_callback(query, "")

                result = await asyncio.wait_for(func(update, context), timeout=timeout)

                await track_callback_end(user_id)
                logger.info("✅ [%s] Callback обработан успешно: %s", user_id, handler_name)
                return result

            except asyncio.TimeoutError:
                await track_callback_end(user_id)
                logger.error("⏰ [%s] Таймаут callback handler (%ss): %s", user_id, timeout, handler_name)
                await emergency_conversation_reset(user_id, context)
                await _return_to_main_menu(query, user_id)
                return ConversationHandler.END

            except Exception as exc:  # pragma: no cover - логирование ошибок
                await track_callback_end(user_id)
                logger.error(
                    "❌ [%s] Ошибка в callback handler %s: %s",
                    user_id,
                    handler_name,
                    exc,
                    exc_info=True,
                )
                await emergency_conversation_reset(user_id, context)
                await _return_to_main_menu(query, user_id, error=True)
                return ConversationHandler.END

        return wrapper

    return decorator


async def _return_to_main_menu(query, user_id: int, error: bool = False) -> None:
    """Возвращает пользователя в главное меню после сбоя callback."""
    message = (
        "❌ **Произошла ошибка**\n\nПроизведен сброс состояния. Возвращаемся в главное меню..."
        if error
        else "⚠️ **Превышено время ожидания**\n\nПроизведен сброс состояния. Возвращаемся в главное меню..."
    )
    try:
        await safe_edit_message(
            query,
            message,
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode="Markdown",
        )
    except Exception:  # pragma: no cover - безопасная обработка
        pass


__all__ = [
    "callback_handler_protection",
    "cleanup_stuck_callbacks",
    "emergency_conversation_reset",
    "track_callback_start",
    "track_callback_end",
]
