"""Фабрика клавиатур и вспомогательные функции для Telegram-бота."""
from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from src.utils.keyboards import keyboard_factory

from . import state


def create_webapp_url(direction: str, date: Optional[str] = None) -> str:
    """Создаёт URL веб-приложения с предустановленным направлением."""
    # Используем главную страницу сайта вместо API endpoint
    return "https://билет.маршруточка.бел/"


def create_webapp_keyboard(
    direction: Optional[str] = None,
    date: Optional[str] = None,
    additional_buttons: Optional[List[List[InlineKeyboardButton]]] = None,
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с кнопками веб-приложения и дополнительными действиями."""
    keyboard: List[List[InlineKeyboardButton]] = []

    if direction:
        direction_names = {
            "minsk_ostrovets": "🏙️ Минск → Островец",
            "ostrovets_minsk": "🏘️ Островец → Минск",
            "minsk_smorgon": "🏙️ Минск → Сморгонь",
            "smorgon_minsk": "🏘️ Сморгонь → Минск",
            "ostrovets_smorgon": "🏘️ Островец → Сморгонь",
            "smorgon_ostrovets": "🏘️ Сморгонь → Островец",
            "both": "🔄 Оба направления",
            "all": "🔄 Все направления",
        }

        if direction in direction_names:
            web_app = WebAppInfo(url=create_webapp_url(direction, date))
            keyboard.append(
                [InlineKeyboardButton("🌐 Открыть сайт бронирования", web_app=web_app)]
            )

            if "smorgon" in direction:
                keyboard.append(
                    [InlineKeyboardButton("ℹ️ Информация о Сморгони", callback_data="smorgon_info")]
                )
        else:
            web_app = WebAppInfo(url=create_webapp_url(direction, date))
            keyboard.append([
                InlineKeyboardButton("🚌 Открыть сайт маршруточки", web_app=web_app)
            ])
    else:
        web_app = WebAppInfo(url=create_webapp_url("general", date))
        keyboard.append([
            InlineKeyboardButton("🚌 Открыть сайт маршруточки", web_app=web_app)
        ])

    if additional_buttons:
        keyboard.extend(additional_buttons)

    return InlineKeyboardMarkup(keyboard)


def get_date_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для выбора даты."""
    return keyboard_factory.get_date_keyboard()


def get_direction_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для выбора направления."""
    return keyboard_factory.get_direction_keyboard()


def get_time_type_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для выбора типа времени."""
    return keyboard_factory.get_time_type_keyboard()


def get_time_range_keyboard(time_type: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для выбора диапазона времени."""
    return keyboard_factory.get_time_range_keyboard(time_type)


def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру главного меню."""
    is_admin = bool(state.admin_panel and state.admin_panel.is_admin(user_id))
    return keyboard_factory.get_main_menu_keyboard(user_id, is_admin)


__all__ = [
    "create_webapp_url",
    "create_webapp_keyboard",
    "get_date_keyboard",
    "get_direction_keyboard",
    "get_time_type_keyboard",
    "get_time_range_keyboard",
    "get_main_menu_keyboard",
]
