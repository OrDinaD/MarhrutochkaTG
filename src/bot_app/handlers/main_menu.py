"""Обработчики главного меню и базовых действий пользователя."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from src.managers.user_manager import user_manager
from src.utils.telegram_safe import safe_answer_callback, safe_edit_message

from ..callback_management import callback_handler_protection
from ..keyboards import get_main_menu_keyboard
from ..monitoring_service import format_monitor_config


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start."""
    text = (
        "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
        "🛣️ **Направления:** Минск ⇄ Островец\n\n"
        "💡 **Выберите действие:**"
    )
    await update.message.reply_text(
        text,
        reply_markup=get_main_menu_keyboard(update.effective_user.id),
        parse_mode="Markdown",
    )


@callback_handler_protection(timeout=30)
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню."""
    query = update.callback_query
    await safe_answer_callback(query)
    user_id = query.from_user.id

    user_manager.user_data_store.pop(user_id, None)
    context.user_data.clear()

    text = (
        "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
        "🛣️ **Направления:** Минск ⇄ Островец\n\n"
        "💡 **Выберите действие:**"
    )

    await safe_edit_message(
        query,
        text,
        reply_markup=get_main_menu_keyboard(user_id),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Прерывает активный conversation и возвращает в главное меню."""
    return await handle_main_menu(update, context)


async def my_monitors(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает активные мониторинги пользователя."""
    user_id = update.effective_user.id
    active_monitors = user_manager.active_monitors

    if user_id in active_monitors:
        config = active_monitors[user_id]
        config_text = format_monitor_config(config)
        keyboard = [
            [InlineKeyboardButton("🛑 Остановить", callback_data="stop_monitoring")],
            [InlineKeyboardButton("🔧 Изменить", callback_data="setup_monitoring")],
            [InlineKeyboardButton("📱 Проверить сейчас", callback_data="check_now")],
        ]
        await update.message.reply_text(
            f"📊 **Активный мониторинг:**\n\n{config_text}\n\n"
            f"⏰ **Создан:** {config.get('created_at', 'н/д')[:19].replace('T', ' ')}\n\n"
            "💡 **Действия:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
    else:
        keyboard = [[InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")]]
        await update.message.reply_text(
            "📊 **Мониторинг не активен**\n\n"
            "💡 Хотите настроить автоматическую проверку рейсов?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )


__all__ = ["start", "handle_main_menu", "cancel_conversation", "my_monitors"]
