"""Обработчики, связанные с поиском маршрутов."""
from __future__ import annotations

from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from src.utils.telegram_safe import safe_answer_callback, safe_edit_message

from .. import state
from ..callback_management import callback_handler_protection
from ..conversation import SEARCH_DATE, CHOOSE_DATE
from ..keyboards import (
    create_webapp_keyboard,
    get_date_keyboard,
)
from ..logging_utils import logger
from ..parser import init_parser


DIRECTION_MAP: Dict[str, Tuple[str, str]] = {
    "search_dir_minsk_ostrovets": ("Минск", "Островец"),
    "search_dir_ostrovets_minsk": ("Островец", "Минск"),
    "search_dir_minsk_smorgon": ("Минск", "Сморгонь"),
    "search_dir_smorgon_minsk": ("Сморгонь", "Минск"),
    "search_dir_ostrovets_smorgon": ("Островец", "Сморгонь"),
    "search_dir_smorgon_ostrovets": ("Сморгонь", "Островец"),
}

DIRECTION_KEY_BY_PAIR: Dict[Tuple[str, str], str] = {
    ('Минск', 'Островец'): 'minsk_ostrovets',
    ('Островец', 'Минск'): 'ostrovets_minsk',
    ('Минск', 'Сморгонь'): 'minsk_smorgon',
    ('Сморгонь', 'Минск'): 'smorgon_minsk',
    ('Островец', 'Сморгонь'): 'ostrovets_smorgon',
    ('Сморгонь', 'Островец'): 'smorgon_ostrovets',
}

@callback_handler_protection(timeout=15)
async def handle_direction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор предустановленного направления."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    data = query.data

    store = state.user_data_store
    store.setdefault(user_id, {})["search_direction"] = data

    await safe_edit_message(
        query,
        "📅 **Выберите дату для поиска рейсов:**",
        reply_markup=get_date_keyboard(),
        parse_mode="Markdown",
    )
    return SEARCH_DATE


async def handle_search_with_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает поиск для заранее выбранного направления."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    data = query.data
    store = state.user_data_store

    if not data.startswith("date_"):
        return ConversationHandler.END

    selected_date = data.replace("date_", "")
    direction_key = store.get(user_id, {}).get("search_direction")
    if not direction_key or direction_key not in DIRECTION_MAP:
        await safe_edit_message(
            query,
            "❌ **Направление не выбрано. Попробуйте снова.**",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data="search_routes")]]
            ),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    from_city, to_city = DIRECTION_MAP[direction_key]
    await safe_edit_message(
        query,
        (
            f"🔍 **Поиск маршрутов...**\n\n"
            f"📍 **Маршрут:** {from_city} → {to_city}\n"
            f"📅 **Дата:** {selected_date}"
        ),
        parse_mode="Markdown",
    )

    await perform_route_search(query, user_id, from_city, to_city, selected_date)
    return ConversationHandler.END


@callback_handler_protection(timeout=15)
async def handle_regular_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает клавиатуру выбора типа поиска."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙️ Минск → Островец", callback_data="search_dir_minsk_ostrovets")],
        [InlineKeyboardButton("🏘️ Островец → Минск", callback_data="search_dir_ostrovets_minsk")],
        [InlineKeyboardButton("🎯 Выбрать города по отдельности", callback_data="search_by_cities")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")],
    ])

    if update.message:
        await update.message.reply_text(
            "🔍 **Выберите маршрут для поиска:**\n\n"
            "🏙️🏘️ **Популярные направления** - быстрый доступ к самым популярным маршрутам\n"
            "🎯 **По отдельности** - выберите откуда и куда, включая Сморгонь",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        query = update.callback_query
        await safe_answer_callback(query)
        await safe_edit_message(
            query,
            "🔍 **Выберите маршрут для поиска:**\n\n"
            "🏙️🏘️ **Популярные направления** - быстрый доступ к самым популярным маршрутам\n"
            "🎯 **По отдельности** - выберите откуда и куда, включая Сморгонь",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


@callback_handler_protection(timeout=15)
async def handle_search_by_cities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает выбор маршрута по городам."""
    query = update.callback_query
    await safe_answer_callback(query)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙️ Минск", callback_data="from_city_Минск")],
        [InlineKeyboardButton("🏘️ Островец", callback_data="from_city_Островец")],
        [InlineKeyboardButton("🏙️ Сморгонь", callback_data="from_city_Сморгонь")],
        [InlineKeyboardButton("🔙 Назад", callback_data="search_routes")],
    ])

    await safe_edit_message(
        query,
        "📍 **Выберите город отправления:**",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


@callback_handler_protection(timeout=15)
async def handle_from_city_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет выбранный город отправления."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    from_city = query.data.replace("from_city_", "")
    store = state.user_data_store
    store.setdefault(user_id, {})["from_city"] = from_city

    cities = ["Минск", "Островец", "Сморгонь"]
    city_emojis = {"Минск": "🏙️", "Островец": "🏘️", "Сморгонь": "🏙️"}
    keyboard_buttons: List[List[InlineKeyboardButton]] = []
    for city in cities:
        if city != from_city:
            keyboard_buttons.append(
                [InlineKeyboardButton(f"{city_emojis[city]} {city}", callback_data=f"to_city_{city}")]
            )
    keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="search_by_cities")])

    await safe_edit_message(
        query,
        f"📍 **Откуда:** {from_city}\n"
        f"📍 **Выберите город назначения:**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard_buttons),
    )


@callback_handler_protection(timeout=15)
async def handle_to_city_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет выбранный город назначения и предлагает выбрать дату."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    to_city = query.data.replace("to_city_", "")
    store = state.user_data_store
    user_data = store.get(user_id, {})
    from_city = user_data.get("from_city")

    if not from_city:
        await safe_edit_message(
            query,
            "❌ Ошибка: город отправления не выбран. Попробуйте снова.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔄 Начать заново", callback_data="search_routes")]]
            ),
        )
        return ConversationHandler.END

    store.setdefault(user_id, {})["to_city"] = to_city
    store[user_id]["route_selected"] = True

    await safe_edit_message(
        query,
        f"📍 **Маршрут:** {from_city} → {to_city}\n"
        f"📅 **Выберите дату для поиска рейсов:**",
        parse_mode="Markdown",
        reply_markup=get_date_keyboard(),
    )
    return SEARCH_DATE


@callback_handler_protection(timeout=15)
async def handle_date_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор даты для поиска по городам."""
    query = update.callback_query
    await safe_answer_callback(query)

    user_id = query.from_user.id
    data = query.data
    store = state.user_data_store

    if not data.startswith("date_"):
        return SEARCH_DATE

    selected_date = data.replace("date_", "")
    user_data = store.get(user_id, {})
    from_city = user_data.get("from_city")
    to_city = user_data.get("to_city")

    if not (from_city and to_city):
        await safe_edit_message(
            query,
            "❌ Не удалось определить маршрут. Попробуйте снова.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔄 Начать заново", callback_data="search_routes")]]
            ),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await safe_edit_message(
        query,
        f"🔍 **Поиск маршрутов...**\n\n📍 {from_city} → {to_city}\n📅 {selected_date}",
        parse_mode="Markdown",
    )

    await perform_route_search(query, user_id, from_city, to_city, selected_date)
    return ConversationHandler.END


async def perform_route_search(query, user_id: int, from_city: str, to_city: str, date: str):
    """Выполняет поиск маршрутов и отправляет пользователю сообщение."""
    try:
        parser = await init_parser()
        routes_data = await parser.get_all_routes(date)

        direction_map = {
            ("Минск", "Островец"): "minsk_to_ostrovets",
            ("Островец", "Минск"): "ostrovets_to_minsk",
            ("Минск", "Сморгонь"): "minsk_to_smorgon",
            ("Сморгонь", "Минск"): "smorgon_to_minsk",
            ("Островец", "Сморгонь"): "ostrovets_to_smorgon",
            ("Сморгонь", "Островец"): "smorgon_to_ostrovets",
        }
        routes_key = direction_map.get((from_city, to_city))

        if routes_key:
            relevant_routes = routes_data.get(routes_key, [])
            message = format_specific_routes(relevant_routes, from_city, to_city, date)
        else:
            message = f"❌ **Направление {from_city} → {to_city} не поддерживается**"

        keyboard = [
            [InlineKeyboardButton("🔍 Новый поиск", callback_data="search_routes")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")],
        ]
        webapp_keyboard = create_webapp_keyboard(
            DIRECTION_KEY_BY_PAIR.get((from_city, to_city)),
            date,
            keyboard,
        )

        await safe_edit_message(
            query,
            message,
            parse_mode="Markdown",
            reply_markup=webapp_keyboard,
        )
    except Exception as exc:
        logger.error("Ошибка поиска маршрутов %s → %s: %s", from_city, to_city, exc)
        await safe_edit_message(
            query,
            f"❌ **Ошибка поиска рейсов {from_city} → {to_city}**\n\n"
            "Попробуйте позже или выберите другое направление.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data="search_by_cities")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")],
                ]
            ),
        )
    finally:
        store = state.user_data_store
        if user_id in store:
            store[user_id].pop("from_city", None)
            store[user_id].pop("to_city", None)
            store[user_id].pop("date", None)
            store[user_id].pop("route_selected", None)
            store[user_id].pop("search_direction", None)


def format_specific_routes(routes: List[Dict], from_city: str, to_city: str, date: str, *, include_header: bool = True) -> str:
    """Форматирует сообщение о найденных маршрутах."""
    if not routes:
        header = f"Рейсы {from_city} → {to_city} на {date}" if include_header else f"{from_city} → {to_city}"
        message = (
            f"❌ **{header} не найдены**\n\n"
            "Попробуйте:\n• Выбрать другую дату\n• Проверить доступность маршрута"
        )
        if from_city == "Сморгонь" or to_city == "Сморгонь":
            message += "\n• Поискать транзитные рейсы через Минск"
        return message

    lines = []
    if include_header:
        lines.extend([f"📅 **Рейсы {from_city} → {to_city} на {date}**", ""])
    for idx, route in enumerate(routes[:8], 1):
        seats = route.get("available_seats", 0)
        if route.get("via_smorgon") and from_city == "Минск" and to_city == "Островец":
            departure_time = route.get("departure_time")
            smorgon_departure = route.get("smorgon_departure", "")
            arrival_time = route.get("arrival_time")
            duration = route.get("duration", "н/д")
            lines.append(f"{idx}. Минск {departure_time}")
            if smorgon_departure and arrival_time:
                smorgon_duration_minutes = route.get("calculated_smorgon_ostrovets_minutes", 65)
                smorgon_hours = smorgon_duration_minutes // 60
                smorgon_mins = smorgon_duration_minutes % 60
                if smorgon_hours > 0:
                    smorgon_duration = f"{smorgon_hours} ч {smorgon_mins} мин"
                else:
                    smorgon_duration = f"{smorgon_mins} мин"
                lines.append(f"   {smorgon_departure} → {arrival_time} ({smorgon_duration})")
            else:
                lines.append(f"   → {arrival_time} ({duration})")
        else:
            time_info = f"**{route.get('departure_time')} → {route.get('arrival_time')}**"
            duration = route.get("duration", "н/д")
            lines.append(f"{idx}. {time_info} ({duration})")

        if seats is not None and not (from_city == "Сморгонь" and to_city == "Островец"):
            seat_emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
            lines.append(f"   {seat_emoji} {seats} мест")

        if route.get("via_smorgon") and not (from_city == "Минск" and to_city == "Островец"):
            lines.append("   🛣️ *через Сморгонь*")
        elif route.get("via_oshmiany"):
            lines.append("   🛣️ *через Ошмяны*")

        lines.append("")

    if from_city == "Сморгонь" or to_city == "Сморгонь":
        lines.append("💡 *Маршруты через Сморгонь могут включать пересадки*")

    return "\n".join(lines)


__all__ = [
    "handle_direction_choice",
    "handle_regular_search",
    "handle_search_by_cities",
    "handle_from_city_choice",
    "handle_to_city_choice",
    "handle_date_choice",
    "handle_search_with_direction",
    "perform_route_search",
    "format_specific_routes",
]
