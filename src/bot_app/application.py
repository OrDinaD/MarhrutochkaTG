"""Основное приложение Telegram-бота."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import traceback
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
)
from telegram.warnings import PTBUserWarning

from src.admin_panel import AdminPanel
from src.security import security
from src.utils.route_analyzer import RouteAnalyzer
from src.utils.telegram_safe import safe_answer_callback, safe_edit_message

from . import state
from .callback_management import (
    callback_handler_protection,
    cleanup_stuck_callbacks,
    emergency_conversation_reset,
)
from .conversation import (
    CHOOSE_DATE,
    CHOOSE_DIRECTION,
    CHOOSE_TIME_RANGE,
    CHOOSE_TIME_TYPE,
    CONFIRM_MONITORING,
    SEARCH_DATE,
)
from .handlers.main_menu import (
    cancel_conversation,
    handle_main_menu,
    my_monitors,
    start,
)
from .handlers.monitoring import (
    handle_custom_time_range_input,
    handle_date_choice as handle_monitoring_date_choice,
    handle_monitoring_confirmation,
    handle_monitoring_direction_choice,
    handle_time_range_choice,
    handle_time_type_choice,
    start_monitoring_conversation,
)
from .handlers.search import (
    format_specific_routes,
    handle_date_choice as handle_search_date_choice,
    handle_direction_choice,
    handle_from_city_choice,
    handle_regular_search,
    handle_search_by_cities,
    handle_search_with_direction,
    handle_to_city_choice,
)
from .keyboards import (
    create_webapp_keyboard,
    get_date_keyboard,
    get_direction_keyboard,
    get_main_menu_keyboard,
    get_time_range_keyboard,
)
from .logging_utils import logger, safe_log_admin, safe_log_bot, safe_log_system
from .monitoring_service import (
    check_routes_for_user,
    filter_routes_by_criteria,
    format_monitor_config,
    restart_monitoring_scheduler,
    send_monitoring_notification,
    trigger_bot_restart,
)
from .parser import get_parser, init_parser
from .state import CLEANUP_JOB_NAME, DATA_DIR, RESTART_JOB_NAME
from src.managers.user_manager import user_manager
from src.monitoring import auto_recovery, crash_handler, diagnostic_system

load_dotenv()

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=PTBUserWarning)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирование ошибок из telegram.ext."""
    update_info: Dict[str, Any] = {}
    if hasattr(update, "effective_user") and update.effective_user:
        update_info["user_id"] = update.effective_user.id
    if hasattr(update, "effective_chat") and update.effective_chat:
        update_info["chat_id"] = update.effective_chat.id
    if hasattr(update, "effective_message") and update.effective_message:
        update_info["message_id"] = update.effective_message.message_id

    safe_log_bot("Ошибка при обработке update", update_info, level="error")
    logger.error("Exception details:", exc_info=context.error)


def create_webapp_url(direction: str, date: Optional[str] = None) -> str:
    """Создаёт URL веб-приложения маршруточки."""
    return "https://билет.маршруточка.бел/"


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения пользователей."""
    user_id = update.effective_user.id
    text = security.sanitize_input(update.message.text)

    store = state.user_data_store
    if user_id not in store:
        await handle_regular_search(update, context)
        return

    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        try:
            datetime.strptime(text, "%Y-%m-%d")
            store[user_id]["date"] = text
            await update.message.reply_text(
                f"✅ **Выбрана дата:** {text}\n\n"
                "🛣️ **Шаг 2:** Выберите направление:",
                reply_markup=get_direction_keyboard(),
                parse_mode="Markdown",
            )
            return CHOOSE_DIRECTION
        except ValueError:
            await update.message.reply_text(
                "❌ **Неверный формат даты**\n\n"
                "Используйте формат YYYY-MM-DD, например: `2025-01-15`",
                parse_mode="Markdown",
            )
            return CHOOSE_DATE

    custom_range_state = await handle_custom_time_range_input(update, context)
    if custom_range_state is not None:
        return custom_range_state

    if user_id in store:
        if "date" not in store[user_id]:
            await update.message.reply_text(
                "❌ **Неверный формат**\n\n"
                "Ожидается дата в формате YYYY-MM-DD, например: `2025-01-15`",
                parse_mode="Markdown",
            )
            return CHOOSE_DATE
        if store[user_id].get("time_type") and "time_range" not in store[user_id]:
            await update.message.reply_text(
                "❌ **Неверный формат времени**\n\n"
                "Ожидается диапазон времени в формате ЧЧ:ММ-ЧЧ:ММ, например:\n"
                "• `07:00-09:00`\n"
                "• `22:00-02:00`",
                parse_mode="Markdown",
            )
            return CHOOSE_TIME_RANGE

    await handle_regular_search(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возвращает справочную информацию."""
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
    help_text = (
        "❓ **Справка по использованию**\n\n"
        "🔍 **Поиск рейсов:**\n"
        "• Отправьте дату в формате YYYY-MM-DD\n"
        "• Например: `2025-01-15`\n\n"
        "🔔 **Мониторинг:**\n"
        "• Выберите дату, направление и время\n"
        "• Бот проверяет каждые 5 минут\n"
        "• Уведомления при появлении мест\n\n"
        "📊 **Команды:**\n"
        "• `/start` - главное меню\n"
        "• `/monitoring` - управление мониторингом\n"
        "• `/profile` - ваш профиль\n"
        "• `/help` - эта справка\n\n"
        "🛠 **Система диагностики (админ):**\n"
        "• `/status` - статус системы мониторинга крашей\n"
        "• `/recovery_history` - история восстановлений\n"
        "• `/system_health` - проверка здоровья системы\n\n"
        "🚌 **Направления:**\n"
        "• Минск → Островец\n"
        "• Островец → Минск"
    )
    await update.message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статус системы диагностики."""
    user_id = update.effective_user.id
    if state.admin_panel and not state.admin_panel.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return

    status_info = {
        "crash_handler": crash_handler is not None,
        "diagnostic_system": diagnostic_system is not None,
        "auto_recovery": auto_recovery is not None,
        "railway_environment": bool(os.getenv("RAILWAY_SERVICE_NAME")),
        "github_token": bool(os.getenv("GITHUB_TOKEN")),
        "telegram_notifications": bool(os.getenv("ADMIN_TELEGRAM_ID")),
        "crash_logs_count": len(list(Path("crash_logs").glob("*.json"))) if Path("crash_logs").exists() else 0,
        "recovery_attempts": len(auto_recovery.recovery_log) if auto_recovery else 0,
    }
    status_text = (
        "🛡️ **СТАТУС СИСТЕМЫ ДИАГНОСТИКИ**\n\n"
        "🔧 **Компоненты:**\n"
        f"• Crash Handler: {'✅ Активен' if status_info['crash_handler'] else '❌ Неактивен'}\n"
        f"• Диагностическая система: {'✅ Активна' if status_info['diagnostic_system'] else '❌ Неактивна'}\n"
        f"• Автовосстановление: {'✅ Активно' if status_info['auto_recovery'] else '❌ Неактивно'}\n\n"
        "🌐 **Окружение:**\n"
        f"• Railway: {'✅ Да' if status_info['railway_environment'] else '❌ Нет'}\n"
        f"• GitHub токен: {'✅ Настроен' if status_info['github_token'] else '❌ Отсутствует'}\n"
        f"• Telegram уведомления: {'✅ Настроены' if status_info['telegram_notifications'] else '❌ Отсутствуют'}\n\n"
        "📊 **Статистика:**\n"
        f"• Логов крашей: {status_info['crash_logs_count']}\n"
        f"• Попыток восстановления: {status_info['recovery_attempts']}\n\n"
        f"⏰ **Последняя проверка:** {datetime.now().strftime('%H:%M:%S')}"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")


async def recovery_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает историю автоматических восстановлений."""
    user_id = update.effective_user.id
    if state.admin_panel and not state.admin_panel.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return

    history = auto_recovery.recovery_log if auto_recovery else []
    if not history:
        await update.message.reply_text("ℹ️ История восстановлений пуста")
        return

    parts = ["🛠 **История автоматических восстановлений:**\n"]
    for entry in history[-10:]:
        parts.append(
            "• {timestamp} — {status}".format(
                timestamp=entry.get("timestamp", "неизвестно"),
                status="успех" if entry.get("success") else "ошибка",
            )
        )
    await update.message.reply_text("\n".join(parts))


async def system_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка состояния систем бота."""
    user_id = update.effective_user.id
    if state.admin_panel and not state.admin_panel.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return

    health_report = diagnostic_system.run_full_health_check() if diagnostic_system else {}
    await update.message.reply_text(
        "🩺 **Проверка системы**\n\n" + json.dumps(health_report, ensure_ascii=False, indent=2),
        parse_mode="Markdown",
    )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает информацию о пользователе."""
    user = update.effective_user
    monitors = state.active_monitors.get(user.id)
    monitors_info = format_monitor_config(monitors) if monitors else "Мониторинг не активен"
    profile_text = (
        "👤 **Ваш профиль**\n\n"
        f"🆔 ID: `{user.id}`\n"
        f"💬 Имя: {user.full_name}\n"
        f"📊 Мониторинг: {monitors_info}"
    )
    await update.message.reply_text(profile_text, parse_mode="Markdown")


async def monitoring_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /monitoring."""
    user_id = update.effective_user.id
    monitors = state.active_monitors.get(user_id)
    if monitors:
        config_text = format_monitor_config(monitors)
        keyboard = [
            [InlineKeyboardButton("🛑 Остановить", callback_data="stop_monitoring")],
            [InlineKeyboardButton("🔧 Изменить", callback_data="setup_monitoring")],
            [InlineKeyboardButton("📱 Проверить сейчас", callback_data="check_now")],
        ]
        await update.message.reply_text(
            f"📊 **Активный мониторинг:**\n\n{config_text}\n\n"
            f"⏰ **Создан:** {monitors.get('created_at', 'н/д')[:19].replace('T', ' ')}\n\n"
            "💡 **Действия:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    keyboard = [[InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")]]
    await update.message.reply_text(
        "📊 **Мониторинг не активен**\n\n"
        "💡 Хотите настроить автоматическую проверку рейсов?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def emergency_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Экстренный сброс состояния пользователя."""
    user_id = update.effective_user.id
    await emergency_conversation_reset(user_id, context)
    text = (
        "🚨 **Экстренный сброс выполнен**\n\n"
        f"👤 **Пользователь:** {user_id}\n"
        "🧹 **Статус:** все состояния сброшены\n\n"
        "✅ Бот готов к работе!"
    )
    await update.message.reply_text(
        text,
        reply_markup=get_main_menu_keyboard(user_id),
        parse_mode="Markdown",
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик callback-кнопок."""
    query = update.callback_query
    data = query.data or ""
    user_id = query.from_user.id

    await safe_answer_callback(query)

    if data == "back_to_main":
        state.user_data_store.pop(user_id, None)
        context.user_data.clear()
        await safe_edit_message(
            query,
            "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
            "🛣️ **Направления:** Минск ⇄ Островец\n\n"
            "💡 **Выберите действие:**",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    if data == "search_routes":
        await handle_regular_search(update, context)
        return
    if data == "search_by_cities":
        await handle_search_by_cities(update, context)
        return
    if data.startswith("search_dir_"):
        await handle_direction_choice(update, context)
        return
    if data.startswith("from_city_"):
        await handle_from_city_choice(update, context)
        return
    if data.startswith("to_city_"):
        await handle_to_city_choice(update, context)
        return
    if data.startswith("date_") and user_id in state.user_data_store and state.user_data_store[user_id].get("route_selected"):
        await handle_search_date_choice(update, context)
        return ConversationHandler.END
    if data.startswith("date_") and user_id in state.user_data_store and "search_direction" in state.user_data_store[user_id]:
        await handle_search_with_direction(update, context)
        return ConversationHandler.END
    if data.startswith("date_") and user_id not in state.user_data_store:
        selected_date = data.replace("date_", "")
        await safe_edit_message(
            query,
            f"🔍 **Ищу рейсы на {selected_date}...**",
            parse_mode="Markdown",
        )
        await init_parser()
        routes_data = await get_parser().get_all_routes(selected_date)
        message = format_routes_message(routes_data, selected_date)
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
        await safe_edit_message(
            query,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    if data == "setup_monitoring":
        return await start_monitoring_conversation(update, context)
    if data == "stop_monitoring":
        return await stop_monitoring(update, context)
    if data == "check_now":
        return await handle_check_now(update, context)
    if data == "my_monitors":
        return await my_monitors(update, context)
    if data in {"confirm_yes", "confirm_no", "back_to_time_range", "back_to_time_type"}:
        return await handle_monitoring_confirmation(update, context)
    if data == "help":
        await help_command(update, context)
        return ConversationHandler.END
    if data == "admin_panel":
        await handle_admin_panel(update, context)
        return ConversationHandler.END
    if data.startswith("admin_"):
        await handle_admin_functions(update, context, data)
        return ConversationHandler.END
    if data == "smorgon_info":
        warning_message = RouteAnalyzer.generate_smorgon_warning()
        await safe_edit_message(
            query,
            warning_message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="search_routes")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")],
            ]),
        )
        return ConversationHandler.END

    if data == "open_website":
        await safe_edit_message(
            query,
            "🌐 **Официальный сайт маршруточки**\n\n"
            "Вы можете посетить официальный сайт для бронирования билетов:\n\n"
            "🔗 **[билет.маршруточка.бел](https://билет.маршруточка.бел/)**\n\n"
            "💡 Нажмите на ссылку выше или используйте веб-приложение ниже:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Открыть веб-приложение", web_app=WebAppInfo(url=create_webapp_url("general")))],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")],
            ]),
            parse_mode="Markdown",
        )
        return ConversationHandler.END


def format_routes_message(routes_data: Dict[str, Any], date: str, direction: str = "all") -> str:
    """Форматирует сообщение со списком рейсов."""
    if not routes_data.get("success", False):
        return "❌ **Не удалось получить данные**"

    direction_mapping = {
        "search_dir_minsk_ostrovets": "minsk_ostrovets",
        "search_dir_ostrovets_minsk": "ostrovets_minsk",
        "search_dir_minsk_smorgon": "minsk_smorgon",
        "search_dir_smorgon_minsk": "smorgon_minsk",
        "search_dir_ostrovets_smorgon": "ostrovets_smorgon",
        "search_dir_smorgon_ostrovets": "smorgon_ostrovets",
        "search_dir_both": "both",
        "search_dir_all": "all",
    }
    if direction in direction_mapping:
        direction = direction_mapping[direction]

    parts = [f"📅 **Рейсы на {date}**", ""]

    sections = {
        "minsk_ostrovets": routes_data.get("minsk_to_ostrovets", [])[:8],
        "ostrovets_minsk": routes_data.get("ostrovets_to_minsk", [])[:8],
        "minsk_smorgon": routes_data.get("minsk_to_smorgon", [])[:8],
        "smorgon_minsk": routes_data.get("smorgon_to_minsk", [])[:8],
        "ostrovets_smorgon": routes_data.get("ostrovets_to_smorgon", [])[:8],
        "smorgon_ostrovets": routes_data.get("smorgon_to_ostrovets", [])[:8],
    }

    titles = {
        "minsk_ostrovets": "Минск → Островец",
        "ostrovets_minsk": "Островец → Минск",
        "minsk_smorgon": "Минск → Сморгонь",
        "smorgon_minsk": "Сморгонь → Минск",
        "ostrovets_smorgon": "Островец → Сморгонь",
        "smorgon_ostrovets": "Сморгонь → Островец",
    }

    for key, routes in sections.items():
        if direction not in {"all", "both", key} and not (
            direction == "both" and key in {"minsk_ostrovets", "ostrovets_minsk"}
        ):
            continue
        if not routes:
            continue
        parts.append(f"🚌 **{titles[key]}:**")
        for formatted in format_specific_routes(routes, titles[key].split(" → ")[0], titles[key].split(" → ")[1], date, include_header=False).split("\n"):
            if formatted:
                parts.append(formatted)
        parts.append("")

    return "\n".join(parts)


async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Останавливает активный мониторинг пользователя."""
    query = update.callback_query
    user_id = query.from_user.id
    if user_manager.remove_user_monitor(user_id):
        if state.job_queue:
            for job in state.job_queue.get_jobs_by_name(f"monitor_{user_id}"):
                job.schedule_removal()
        await safe_edit_message(
            query,
            "✅ **Мониторинг остановлен**\n\n"
            "💡 Для настройки нового мониторинга используйте /start",
            parse_mode="Markdown",
        )
    else:
        await safe_edit_message(
            query,
            "ℹ️ **Мониторинг не был активен**",
            parse_mode="Markdown",
        )
    return ConversationHandler.END


async def handle_check_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Проверяет рейсы немедленно."""
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in state.active_monitors:
        await safe_answer_callback(query, "❌ Мониторинг не активен")
        return ConversationHandler.END

    await safe_answer_callback(query, "🔍 Проверяю рейсы...")

    class FakeJob:
        def __init__(self, data: int):
            self.data = data

    class FakeContext:
        def __init__(self, bot):
            self.bot = bot
            self.job = FakeJob(user_id)

    fake_context = FakeContext(query.bot)
    await check_routes_for_user(fake_context)

    await safe_edit_message(
        query,
        "✅ **Проверка завершена**\n\n"
        "Если найдены подходящие рейсы, вы получите уведомление.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main"),
                ]
            ]
        ),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not state.admin_panel or not state.admin_panel.is_admin(update.effective_user.id):
        await safe_edit_message(
            update.callback_query,
            "❌ Админ-панель недоступна",
            parse_mode="Markdown",
        )
        return

    await safe_edit_message(
        update.callback_query,
        "👨‍💻 **Админ-панель**\n\nВыберите раздел:",
        reply_markup=state.admin_panel.get_main_keyboard(),
        parse_mode="Markdown",
    )


async def handle_admin_functions(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    if not state.admin_panel or not state.admin_panel.is_admin(update.effective_user.id):
        await safe_edit_message(
            update.callback_query,
            "❌ Админ-панель недоступна",
            parse_mode="Markdown",
        )
        return

    query = update.callback_query
    if action == "admin_routes_info":
        await safe_edit_message(
            query,
            state.admin_panel.get_routes_info(),
            reply_markup=state.admin_panel.get_routes_keyboard(),
            parse_mode="Markdown",
        )
        return

    if action == "admin_system_logs":
        await safe_edit_message(
            query,
            state.admin_panel.get_system_logs(),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔄 Обновить", callback_data="admin_system_logs")],
                    [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")],
                ]
            ),
            parse_mode="Markdown",
        )
        return

    if action == "admin_bot_settings":
        await safe_edit_message(
            query,
            state.admin_panel.get_bot_settings(),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔄 Обновить", callback_data="admin_bot_settings")],
                    [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")],
                ]
            ),
            parse_mode="Markdown",
        )
        return

    if action == "admin_restart_bot":
        await safe_edit_message(
            query,
            "🔁 **ПЕРЕЗАГРУЗКА БОТА**\n\n"
            "⚠️ После подтверждения бот будет остановлен и автоматически запущен заново.\n"
            "Активные мониторинги восстановятся после перезапуска.",
            reply_markup=state.admin_panel.get_restart_confirmation_keyboard(),
            parse_mode="Markdown",
        )
        return

    if action == "admin_restart_bot_confirm":
        await schedule_bot_restart(update, context)
        return

    if action == "admin_restart_scheduler":
        scheduler_result = await restart_monitoring_scheduler()
        keyboard = [
            [InlineKeyboardButton("🔙 Экстренные функции", callback_data="admin_emergency")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")],
        ]
        message_text = (
            "🔄 **ПЕРЕЗАПУСК ПЛАНИРОВЩИКА**\n\n"
            f"🗑️ Удалено задач: {scheduler_result.get('jobs_removed', 0)}\n"
            f"🔔 Восстановлено мониторингов: {scheduler_result.get('monitors_restored', 0)}"
        )
        if not scheduler_result.get("success"):
            message_text = (
                "❌ **ОШИБКА ПЕРЕЗАПУСКА ПЛАНИРОВЩИКА**\n\n"
                f"Причина: `{scheduler_result.get('reason', 'unknown')}`"
            )
        await safe_edit_message(
            query,
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    if action == "admin_emergency":
        await safe_edit_message(
            query,
            "🚨 **ЭКСТРЕННЫЕ ФУНКЦИИ**\n\n"
            "⚠️ **ВНИМАНИЕ!** Эти функции могут повлиять на работу бота.\n"
            "Используйте их только при необходимости.\n\n"
            "💡 Выберите действие:",
            reply_markup=state.admin_panel.get_emergency_functions_keyboard(),
            parse_mode="Markdown",
        )
        return

    if action == "admin_stop_all_monitoring":
        result = state.admin_panel.stop_all_monitoring(state.active_monitors, state.job_queue)
        await safe_edit_message(
            query,
            result,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔙 Экстренные функции", callback_data="admin_emergency")],
                    [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")],
                ]
            ),
            parse_mode="Markdown",
        )
        return

    if action == "admin_clear_user_cache":
        result = state.admin_panel.clear_user_cache(state.user_data_store)
        await safe_edit_message(
            query,
            result,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔙 Экстренные функции", callback_data="admin_emergency")],
                    [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")],
                ]
            ),
            parse_mode="Markdown",
        )
        return

    if action == "admin_export_data":
        await safe_answer_callback(query, "📤 Экспортирую данные...")
        export_result = state.admin_panel.export_data(state.active_monitors)
        if export_result["success"]:
            message_text = (
                "📤 **ЭКСПОРТ ДАННЫХ ЗАВЕРШЕН**\n\n"
                f"✅ Данные сохранены в файл:\n`{export_result['filename']}`\n\n"
                f"📊 **Статистика:**\n• Мониторингов: {len(state.active_monitors)}\n"
                f"• Пользователей: {export_result['data']['total_users']}\n"
                f"• Дата экспорта: {export_result['data']['timestamp'][:19].replace('T', ' ')}"
            )
        else:
            message_text = f"📤 **ОШИБКА ЭКСПОРТА**\n\n❌ {export_result['error']}"
        await safe_edit_message(
            query,
            message_text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔙 Экстренные функции", callback_data="admin_emergency")],
                    [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")],
                ]
            ),
            parse_mode="Markdown",
        )
        return


async def schedule_bot_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]]
    delay_seconds = 3
    restart_info = context.application.bot_data.get("restart_info", {})
    pending = restart_info.get("pending", False)

    if pending:
        requested_at_iso = restart_info.get("requested_at")
        scheduled_for_iso = restart_info.get("scheduled_for")
        requested_at = (
            datetime.fromisoformat(requested_at_iso).strftime("%d.%m.%Y %H:%M:%S")
            if requested_at_iso
            else "неизвестно"
        )
        scheduled_time = (
            datetime.fromisoformat(scheduled_for_iso).strftime("%d.%m.%Y %H:%M:%S")
            if scheduled_for_iso
            else "неизвестно"
        )
        message_text = (
            "⚠️ **ПЕРЕЗАГРУЗКА УЖЕ ЗАПЛАНИРОВАНА**\n\n"
            f"🕒 Запрос: {requested_at}\n"
            f"🚀 Ожидаемое время: {scheduled_time}"
        )
    else:
        requested_at = datetime.now()
        scheduled_for = requested_at + timedelta(seconds=delay_seconds)
        context.application.bot_data["restart_info"] = {
            "pending": True,
            "requested_at": requested_at.isoformat(),
            "scheduled_for": scheduled_for.isoformat(),
            "delay_seconds": delay_seconds,
        }
        if context.application.job_queue:
            for job in context.application.job_queue.get_jobs_by_name(RESTART_JOB_NAME):
                job.schedule_removal()
            context.application.job_queue.run_once(
                trigger_bot_restart,
                when=delay_seconds,
                name=RESTART_JOB_NAME,
            )
        message_text = (
            "🔁 **ПЕРЕЗАГРУЗКА БОТА**\n\n"
            "✅ Перезапуск запланирован.\n"
            f"🕒 Запрос: {requested_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"🚀 Ожидаемое время перезапуска: {scheduled_for.strftime('%d.%m.%Y %H:%М:%S')}\n"
            f"⏳ Задержка: {delay_seconds} сек.\n\n"
            "Бот автоматически завершит работу и перезапустится."
        )
    await safe_edit_message(
        query,
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


def register_handlers(application: Application) -> None:
    monitoring_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_monitoring_conversation, pattern="^setup_monitoring$")],
        states={
            CHOOSE_DATE: [
                CallbackQueryHandler(handle_monitoring_date_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input),
            ],
            CHOOSE_DIRECTION: [CallbackQueryHandler(handle_monitoring_direction_choice)],
            CHOOSE_TIME_TYPE: [CallbackQueryHandler(handle_time_type_choice)],
            CHOOSE_TIME_RANGE: [
                CallbackQueryHandler(handle_time_range_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input),
            ],
            CONFIRM_MONITORING: [CallbackQueryHandler(handle_monitoring_confirmation)],
        },
        fallbacks=[CallbackQueryHandler(handle_main_menu, pattern="^back_to_main$")],
    )

    application.add_handler(monitoring_conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("recovery_history", recovery_history_command))
    application.add_handler(CommandHandler("system_health", system_health_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("monitoring", monitoring_command))
    application.add_handler(CommandHandler("reset", emergency_reset_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.add_error_handler(error_handler)


def main() -> None:
    """Точка входа в приложение бота."""
    safe_log_system("Мониторинги работают в memory-only режиме", {})

    try:
        crash_handler.setup_crash_handling()
        safe_log_system("Система обработки крашей активирована", {"status": "enabled"})
    except Exception as exc:
        safe_log_system("Ошибка активации crash handler", {"error": str(exc)}, level="error")

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        safe_log_bot("Токен бота не найден", {"error": "TELEGRAM_BOT_TOKEN missing"}, level="error")
        return

    admin_telegram_id = os.getenv("ADMIN_TELEGRAM_ID")
    if admin_telegram_id:
        try:
            state.admin_panel = AdminPanel(int(admin_telegram_id))
            safe_log_admin("Админ-панель активирована", {"admin_id": admin_telegram_id})
        except ValueError:
            safe_log_admin("Неверный ADMIN_TELEGRAM_ID", {"error": "must_be_number"}, level="error")
    else:
        safe_log_admin("ADMIN_TELEGRAM_ID не установлен", {"warning": "admin_panel_disabled"}, level="warning")

    safe_log_bot(
        "Запуск бота MarhrutochkaTG",
        {
            "python_version": sys.version.split()[0],
            "working_directory": os.getcwd(),
            "process_id": os.getpid(),
            "environment": "railway" if os.getenv("RAILWAY_SERVICE_NAME") else "local",
        },
    )

    persistence_path = os.path.join(DATA_DIR, "bot_state.pickle")
    persistence = PicklePersistence(filepath=persistence_path)
    application = Application.builder().token(token).persistence(persistence).build()

    try:
        register_handlers(application)
        state.job_queue = application.job_queue

        monitors_storage = application.bot_data.setdefault("active_monitors", {})
        user_data_storage = application.bot_data.setdefault("user_data_store", {})
        user_manager.bind_active_monitors(monitors_storage)
        user_manager.bind_user_data_store(user_data_storage)
        state.active_monitors = user_manager.active_monitors
        state.user_data_store = user_manager.user_data_store

        state.job_queue.run_repeating(
            cleanup_stuck_callbacks,
            interval=30,
            first=10,
            name=CLEANUP_JOB_NAME,
        )

        safe_log_bot(
            "Данные восстановлены",
            {
                "monitors_count": len(state.active_monitors),
                "mode": "memory-only",
                "callback_cleanup": "enabled",
            },
        )

        for user_id in state.active_monitors.keys():
            try:
                state.job_queue.run_repeating(
                    check_routes_for_user,
                    interval=300,
                    first=10,
                    name=f"monitor_{user_id}",
                    data=user_id,
                )
                safe_log_bot("Мониторинг восстановлен", {"user_id": user_id})
            except Exception as exc:
                safe_log_bot(
                    "Ошибка восстановления мониторинга",
                    {"user_id": user_id, "error": str(exc)},
                    level="error",
                )

        state.application = application
        safe_log_bot("Бот запущен успешно", {"status": "running"})
        application.run_polling(drop_pending_updates=True)

        restart_info = application.bot_data.get("restart_info", {})
        if restart_info.get("pending"):
            safe_log_system("Перезапуск бота: выполняем рестарт процесса", restart_info)
            restart_info["pending"] = False
            logging.shutdown()
            os.execl(sys.executable, sys.executable, *sys.argv)

    except Conflict:
        safe_log_bot("Конфликт: бот уже запущен", {"error": "conflict"}, level="error")
    except Exception as exc:
        safe_log_bot("Критическая ошибка", {"error": str(exc)}, level="error")

        try:
            async def handle_crash() -> None:
                crash_analysis = await diagnostic_system.analyze_crash_report_from_exception(exc)
                if crash_analysis:
                    recovery_result = await auto_recovery.attempt_auto_recovery(crash_analysis)
                    safe_log_system(
                        "Автоматическое восстановление завершено",
                        {
                            "success": recovery_result.get("success", False),
                            "actions_count": len(recovery_result.get("actions_taken", [])),
                            "crash_id": crash_analysis.get("crash_id"),
                        },
                    )

            asyncio.run(handle_crash())
        except Exception as recovery_error:
            safe_log_system("Ошибка автоматического восстановления", {"error": str(recovery_error)}, level="error")

        traceback.print_exc()
    finally:
        try:
            if state.job_queue:
                for job in state.job_queue.jobs():
                    job.schedule_removal()
                logger.info("⏰ JobQueue остановлен")
        except Exception as exc:
            logger.error(f"Ошибка при завершении JobQueue: {exc}", exc_info=True)


if __name__ == "__main__":
    try:
        logger.info("🚀 Старт главной функции main()")
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as exc:
        logger.error(f"💥 Фатальная ошибка: {exc}", exc_info=True)
        sys.exit(1)
