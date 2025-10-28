"""Conversation-хендлеры для настройки мониторинга."""
from __future__ import annotations

from typing import Any, Dict, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from src.managers.user_manager import user_manager
from src.utils.telegram_safe import safe_answer_callback, safe_edit_message

from .. import state
from ..callback_management import callback_handler_protection
from ..conversation import (
    CHOOSE_DATE,
    CHOOSE_DIRECTION,
    CHOOSE_TIME_RANGE,
    CHOOSE_TIME_TYPE,
    CONFIRM_MONITORING,
)
from ..keyboards import (
    get_date_keyboard,
    get_direction_keyboard,
    get_time_range_keyboard,
    get_time_type_keyboard,
)
from ..logging_utils import logger
from ..monitoring_service import (
    check_routes_for_user,
    format_monitor_config,
)


async def start_monitoring_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает настройку мониторинга."""
    user_id = update.effective_user.id
    store = state.user_data_store
    store.pop(user_id, None)
    context.user_data.clear()
    store[user_id] = {}

    text = (
        "🔔 **Настройка мониторинга рейсов**\n\n"
        "Я буду проверять появление мест каждые 5 минут и уведомлять вас!\n\n"
        "📅 **Шаг 1:** Выберите дату поездки:"
    )

    if update.callback_query:
        await safe_edit_message(
            update.callback_query,
            text,
            reply_markup=get_date_keyboard(),
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=get_date_keyboard(),
            parse_mode="Markdown",
        )

    return CHOOSE_DATE


@callback_handler_protection(timeout=20)
async def handle_date_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор даты мониторинга."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    data = query.data
    store = state.user_data_store

    if data.startswith("date_"):
        selected_date = data.replace("date_", "")
        store.setdefault(user_id, {})["date"] = selected_date

        user_data = store.get(user_id, {})
        if user_data.get("from_city") and user_data.get("to_city"):
            from .search import perform_route_search

            from_city = user_data["from_city"]
            to_city = user_data["to_city"]

            await safe_edit_message(
                query,
                (
                    "🔍 **Поиск маршрутов...**\n\n"
                    f"📍 **Маршрут:** {from_city} → {to_city}\n"
                    f"📅 **Дата:** {selected_date}"
                ),
                parse_mode="Markdown",
            )

            await perform_route_search(query, user_id, from_city, to_city, selected_date)
            return ConversationHandler.END

        await safe_edit_message(
            query,
            (
                f"✅ **Выбрана дата:** {selected_date}\n\n"
                "🛣️ **Шаг 2:** Выберите направление:"
            ),
            reply_markup=get_direction_keyboard(),
            parse_mode="Markdown",
        )
        return CHOOSE_DIRECTION

    if data == "custom_date":
        await safe_edit_message(
            query,
            (
                "📅 **Введите дату в формате YYYY-MM-DD**\n\n"
                "Например: `2025-01-15`\n\n"
                "Или нажмите кнопку ниже для возврата:"
            ),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Выбрать из списка", callback_data="back_to_date_list")]]
            ),
            parse_mode="Markdown",
        )
        return CHOOSE_DATE

    if data == "back_to_main":
        store.pop(user_id, None)
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск рейсов", callback_data="search_routes")],
            [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
            [InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")],
        ]
        await safe_edit_message(
            query,
            (
                "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
                "🛣️ **Направления:** Минск ⇄ Островец\n"
                "🌐 **Источник:** билет.маршруточка.бел\n\n"
                "💡 **Выберите действие:**"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    return CHOOSE_DATE


@callback_handler_protection(timeout=20)
async def handle_monitoring_direction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора направления."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    data = query.data
    store = state.user_data_store

    if data.startswith("dir_"):
        direction = data.replace("dir_", "")
        store.setdefault(user_id, {})["direction"] = direction
        direction_text = {
            "minsk_ostrovets": "Минск → Островец",
            "ostrovets_minsk": "Островец → Минск",
            "both": "Оба направления",
        }.get(direction, direction)

        await safe_edit_message(
            query,
            f"✅ **Направление:** {direction_text}\n\n",
            "⏰ **Шаг 3:** Что важнее для вас?",
            reply_markup=get_time_type_keyboard(),
            parse_mode="Markdown",
        )
        return CHOOSE_TIME_TYPE

    if data == "back_to_date":
        await safe_edit_message(
            query,
            "📅 **Шаг 1:** Выберите дату поездки:",
            reply_markup=get_date_keyboard(),
            parse_mode="Markdown",
        )
        return CHOOSE_DATE

    return CHOOSE_DIRECTION


@callback_handler_protection(timeout=20)
async def handle_time_type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа времени мониторинга."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    data = query.data
    store = state.user_data_store

    if data.startswith("time_"):
        time_type = data.replace("time_", "")
        store.setdefault(user_id, {})["time_type"] = time_type
        time_text = {
            "departure": "время отправления",
            "arrival": "время прибытия",
            "any": "любое время",
        }.get(time_type, time_type)

        if time_type == "any":
            store[user_id]["time_range"] = "любое время"
            config_text = format_monitor_config(store[user_id])
            await safe_edit_message(
                query,
                f"✅ **Настройки мониторинга:**\n\n{config_text}\n\n",
                "❓ **Запустить мониторинг?**",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("✅ Да, запустить!", callback_data="confirm_yes")],
                        [InlineKeyboardButton("❌ Нет, изменить", callback_data="confirm_no")],
                        [InlineKeyboardButton("🔙 Время", callback_data="back_to_time_type")],
                    ]
                ),
                parse_mode="Markdown",
            )
            return CONFIRM_MONITORING

        await safe_edit_message(
            query,
            f"✅ **Критерий:** {time_text}\n\n",
            "🕐 **Шаг 4:** Выберите желаемый диапазон времени:",
            reply_markup=get_time_range_keyboard(time_type),
            parse_mode="Markdown",
        )
        return CHOOSE_TIME_RANGE

    if data == "back_to_direction":
        direction_text = {
            "minsk_ostrovets": "Минск → Островец",
            "ostrovets_minsk": "Островец → Минск",
            "both": "Оба направления",
        }.get(store.get(user_id, {}).get("direction", ""), store.get(user_id, {}).get("direction", ""))

        await safe_edit_message(
            query,
            f"✅ **Направление:** {direction_text}\n\n",
            "🛣️ **Шаг 2:** Выберите направление:",
            reply_markup=get_direction_keyboard(),
            parse_mode="Markdown",
        )
        return CHOOSE_DIRECTION

    return CHOOSE_TIME_TYPE


@callback_handler_protection(timeout=20)
async def handle_time_range_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор диапазона времени."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    data = query.data
    store = state.user_data_store

    if data == "back_to_range_list":
        time_type = store.get(user_id, {}).get("time_type", "departure")
        await safe_edit_message(
            query,
            "🕐 **Шаг 4:** Выберите желаемый диапазон времени:",
            reply_markup=get_time_range_keyboard(time_type),
            parse_mode="Markdown",
        )
        return CHOOSE_TIME_RANGE

    if data == "back_to_time_range":
        time_type = store.get(user_id, {}).get("time_type", "departure")
        await safe_edit_message(
            query,
            "🕐 **Шаг 4:** Выберите желаемый диапазон времени:",
            reply_markup=get_time_range_keyboard(time_type),
            parse_mode="Markdown",
        )
        return CHOOSE_TIME_RANGE

    if data.startswith("range_"):
        time_range = data.replace("range_", "")
        if time_range == "custom":
            await safe_edit_message(
                query,
                "🕐 **Введите диапазон времени в формате ЧЧ:ММ-ЧЧ:ММ**\n\n"
                "Примеры:\n"
                "• `07:00-09:00` - с 7 до 9 утра\n"
                "• `17:30-19:30` - с 17:30 до 19:30\n\n"
                "Или нажмите кнопку ниже:",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Выбрать из списка", callback_data="back_to_range_list")]]
                ),
                parse_mode="Markdown",
            )
            return CHOOSE_TIME_RANGE

        store.setdefault(user_id, {})["time_range"] = time_range
        config_text = format_monitor_config(store[user_id])
        await safe_edit_message(
            query,
            f"✅ **Настройки мониторинга:**\n\n{config_text}\n\n",
            "❓ **Запустить мониторинг?**",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("✅ Да, запустить!", callback_data="confirm_yes")],
                    [InlineKeyboardButton("❌ Нет, изменить", callback_data="confirm_no")],
                    [InlineKeyboardButton("🔙 Диапазон времени", callback_data="back_to_time_range")],
                ]
            ),
            parse_mode="Markdown",
        )
        return CONFIRM_MONITORING

    return CHOOSE_TIME_RANGE


async def _ensure_monitoring_session(
    user_id: int, query, context: ContextTypes.DEFAULT_TYPE
) -> Optional[Dict[str, Any]]:
    session = state.user_data_store.get(user_id)
    if not session:
        await safe_edit_message(
            query,
            "⚠️ **Настройка мониторинга была сброшена**\n\n",
            "Не удалось найти сохраненные данные. Начните настройку заново.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")],
                ]
            ),
            parse_mode="Markdown",
        )
        return None

    required_fields = ["date", "direction", "time_type", "time_range"]
    missing = [field for field in required_fields if field not in session]
    if missing:
        logger.warning(
            "Недостаточно данных для запуска мониторинга пользователя %s: отсутствует %s",
            user_id,
            missing,
        )
        await safe_edit_message(
            query,
            "⚠️ **Не хватает данных для запуска мониторинга**\n\n",
            "Пожалуйста, пройдите настройку заново.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")],
                ]
            ),
            parse_mode="Markdown",
        )
        return None

    return session.copy()


async def _store_monitoring_config(
    user_id: int, query, context: ContextTypes.DEFAULT_TYPE, session: Dict[str, Any]
) -> None:
    monitor_payload = session.copy()
    monitor_payload["chat_id"] = query.message.chat_id
    user_manager.set_user_monitor(user_id, monitor_payload)
    config = user_manager.get_user_monitor(user_id)

    if state.job_queue:
        try:
            state.job_queue.run_repeating(
                check_routes_for_user,
                interval=300,
                first=10,
                name=f"monitor_{user_id}",
                data=user_id,
            )
        except Exception as exc:
            logger.error(
                "Не удалось добавить задачу мониторинга для пользователя %s: %s",
                user_id,
                exc,
            )

    await safe_edit_message(
        query,
        "🎉 **Мониторинг запущен!**\n\n"
        f"{format_monitor_config(config)}\n\n"
        "✅ Я буду проверять наличие мест каждые 5 минут\n"
        "📱 Уведомления придут как только появятся подходящие рейсы\n\n"
        "💡 Используйте главное меню для управления:",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
        ),
        parse_mode="Markdown",
    )


async def _show_adjust_menu(user_id: int, query):
    if user_id not in state.user_data_store:
        await safe_edit_message(
            query,
            "ℹ️ **Сессия настройки недоступна**\n\n",
            "Начните настройку заново, чтобы изменить параметры.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")],
                ]
            ),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await safe_edit_message(
        query,
        "🔧 **Настройка мониторинга**\n\n",
        "Выберите параметр для изменения:",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("📅 Дата", callback_data="change_date")],
                [InlineKeyboardButton("🛣️ Направление", callback_data="change_direction")],
                [InlineKeyboardButton("⏰ Время", callback_data="change_time_type")],
                [InlineKeyboardButton("🕐 Диапазон", callback_data="change_time_range")],
                [InlineKeyboardButton("✅ Запустить", callback_data="confirm_yes")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")],
            ]
        ),
        parse_mode="Markdown",
    )


@callback_handler_protection(timeout=20)
async def handle_monitoring_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждает запуск мониторинга."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    data = query.data

    if data == "confirm_yes":
        session = await _ensure_monitoring_session(user_id, query, context)
        if session is None:
            return ConversationHandler.END
        await _store_monitoring_config(user_id, query, context, session)
        return ConversationHandler.END

    if data == "confirm_no":
        await _show_adjust_menu(user_id, query)
        return CHOOSE_DATE

    if data == "back_to_time_range":
        time_type = state.user_data_store.get(user_id, {}).get("time_type", "departure")
        await safe_edit_message(
            query,
            "🕐 **Шаг 4:** Выберите желаемый диапазон времени:",
            reply_markup=get_time_range_keyboard(time_type),
            parse_mode="Markdown",
        )
        return CHOOSE_TIME_RANGE

    if data == "back_to_time_type":
        await safe_edit_message(
            query,
            "⏰ **Шаг 3:** Что важнее для вас?",
            reply_markup=get_time_type_keyboard(),
            parse_mode="Markdown",
        )
        return CHOOSE_TIME_TYPE

    return CONFIRM_MONITORING


async def handle_custom_time_range_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[int]:
    """Обрабатывает текстовый ввод диапазона времени."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    store = state.user_data_store

    from src.security import security

    normalized_range = security.normalize_time_range(text)
    if normalized_range:
        store.setdefault(user_id, {})["time_range"] = normalized_range
        config_text = format_monitor_config(store[user_id])
        await update.message.reply_text(
            f"✅ **Настройки мониторинга:**\n\n{config_text}\n\n",
            "❓ **Запустить мониторинг?**",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("✅ Да, запустить!", callback_data="confirm_yes")],
                    [InlineKeyboardButton("❌ Нет, изменить", callback_data="confirm_no")],
                    [InlineKeyboardButton("🔙 Диапазон времени", callback_data="back_to_time_range")],
                ]
            ),
            parse_mode="Markdown",
        )
        return CONFIRM_MONITORING

    if (
        normalized_range is None
        and user_id in store
        and store[user_id].get("time_type")
        and "time_range" not in store[user_id]
    ):
        await update.message.reply_text(
            "❌ **Неверный формат времени**\n\n"
            "Используйте формат ЧЧ:ММ-ЧЧ:ММ, например:\n"
            "• `07:00-09:00` — утренний диапазон\n"
            "• `22:00-02:00` — через полночь\n\n"
            "Допускаются пробелы вокруг дефиса. Часы должны быть от 00 до 23, минуты от 00 до 59.",
            parse_mode="Markdown",
        )
        return CHOOSE_TIME_RANGE

    return None


__all__ = [
    "start_monitoring_conversation",
    "handle_date_choice",
    "handle_monitoring_confirmation",
    "handle_monitoring_direction_choice",
    "handle_time_range_choice",
    "handle_time_type_choice",
    "handle_custom_time_range_input",
]
