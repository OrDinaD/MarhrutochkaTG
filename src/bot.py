#!/usr/bin/env python3
"""
Продвинутый Telegram-бот с настраиваемым мониторингом и работой с профилем
"""

import logging
import warnings
import os
import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.warnings import PTBUserWarning
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Игнорируем предупреждения от python-telegram-bot о per_message
warnings.filterwarnings("ignore", category=UserWarning)

# Отключаем подробные сообщения от httpx, используемого библиотекой telegram
logging.getLogger("httpx").setLevel(logging.WARNING)

# Состояния для ConversationHandler
(CHOOSE_DATE, CHOOSE_DIRECTION, CHOOSE_TIME_TYPE, CHOOSE_TIME_RANGE, 
 CONFIRM_MONITORING, MONITORING_ACTIVE, LOGIN_PHONE, LOGIN_PASSWORD,
 SEARCH_FROM, SEARCH_TO, SEARCH_DATE, BOOKING_NUMBER, PHONE_DIGITS) = range(13)

# Глобальные переменные
parser = None
auth_manager = None
scheduler = AsyncIOScheduler()
active_monitors = {}  # user_id -> monitor_config
user_data_store = {}  # user_id -> user_data
user_auth = {}  # user_id -> auth_status
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'monitors.json')

def load_active_monitors():
    """Загрузка активных мониторингов из файла"""
    global active_monitors
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            active_monitors = {int(k): v for k, v in data.items()}
        except Exception as e:
            logger.error(f"Не удалось загрузить мониторинги: {e}")

def save_active_monitors():
    """Сохранение активных мониторингов в файл"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(active_monitors, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Не удалось сохранить мониторинги: {e}")

# Загружаем существующие мониторинги при импорте модуля
load_active_monitors()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors from telegram.ext and log them."""
    logger.error("Exception while handling an update:", exc_info=context.error)

async def init_parser():
    """Инициализация парсера"""
    global parser
    if parser is None:
        try:
            from .parser import FinalMarshrutochkaParser
        except ImportError:
            from parser import FinalMarshrutochkaParser
        parser = FinalMarshrutochkaParser()
        await parser.__aenter__()

async def init_auth_manager():
    """Инициализация менеджера авторизации"""
    global auth_manager
    if auth_manager is None:
        try:
            from .auth_manager import AuthManager
        except ImportError:
            from auth_manager import AuthManager
        auth_manager = AuthManager()
        await auth_manager.__aenter__()

# ==================== UTILITY FUNCTIONS ====================

def get_date_keyboard():
    """Клавиатура для выбора даты"""
    today = datetime.now()
    dates = []
    
    for i in range(7):  # Показываем 7 дней
        date = today + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        day_name = date.strftime('%A') if i < 3 else date.strftime('%d.%m')
        
        if i == 0:
            label = f"🔵 Сегодня ({day_name})"
        elif i == 1:
            label = f"🟢 Завтра ({day_name})"
        else:
            label = f"📅 {day_name}"
        
        dates.append([InlineKeyboardButton(label, callback_data=f"date_{date_str}")])
    
    dates.append([InlineKeyboardButton("📅 Другая дата", callback_data="custom_date")])
    dates.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(dates)

def get_direction_keyboard():
    """Клавиатура для выбора направления"""
    keyboard = [
        [InlineKeyboardButton("🏙️ Минск → Островец", callback_data="dir_minsk_ostrovets")],
        [InlineKeyboardButton("🏘️ Островец → Минск", callback_data="dir_ostrovets_minsk")],
        [InlineKeyboardButton("🔄 Оба направления", callback_data="dir_both")],
        [InlineKeyboardButton("🔙 Выбрать дату", callback_data="back_to_date")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_time_type_keyboard():
    """Клавиатура для выбора типа времени"""
    keyboard = [
        [InlineKeyboardButton("🚀 Время отправления", callback_data="time_departure")],
        [InlineKeyboardButton("🎯 Время прибытия", callback_data="time_arrival")],
        [InlineKeyboardButton("⏰ Любое время", callback_data="time_any")],
        [InlineKeyboardButton("🔙 Выбрать направление", callback_data="back_to_direction")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_time_range_keyboard(time_type):
    """Клавиатура для выбора диапазона времени"""
    ranges = [
        ("🌅 Утром (05:00-09:00)", "05:00-09:00"),
        ("☀️ Днём (09:00-15:00)", "09:00-15:00"),
        ("🌆 Вечером (15:00-20:00)", "15:00-20:00"),
        ("🌙 Ночью (20:00-05:00)", "20:00-05:00"),
        ("🕐 Пользовательский диапазон", "custom"),
        ("⏰ Любое время", "any")
    ]
    
    keyboard = []
    for label, value in ranges:
        keyboard.append([InlineKeyboardButton(label, callback_data=f"range_{value}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Тип времени", callback_data="back_to_time_type")])
    return InlineKeyboardMarkup(keyboard)

def format_monitor_config(config):
    """Форматирование конфигурации мониторинга"""
    direction_map = {
        "minsk_ostrovets": "Минск → Островец",
        "ostrovets_minsk": "Островец → Минск",
        "both": "Оба направления"
    }
    
    time_type_map = {
        "departure": "отправления",
        "arrival": "прибытия",
        "any": "любое"
    }
    
    parts = [
        f"📅 **Дата:** {config['date']}",
        f"🛣️ **Направление:** {direction_map.get(config['direction'], config['direction'])}",
        f"⏰ **Время:** {time_type_map.get(config['time_type'], config['time_type'])}",
        f"🕐 **Диапазон:** {config['time_range']}",
        f"🔔 **Проверка:** каждые 5 минут"
    ]
    
    return "\n".join(parts)

# ==================== CONVERSATION HANDLERS ====================

async def start_monitoring_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало настройки мониторинга"""
    user_id = update.effective_user.id
    
    # Инициализируем данные пользователя
    user_data_store[user_id] = {}
    
    text = (
        "🔔 **Настройка мониторинга рейсов**\n\n"
        "Я буду проверять появление мест каждые 5 минут и уведомлять вас!\n\n"
        "📅 **Шаг 1:** Выберите дату поездки:"
    )
    
    # Проверяем, это callback query или обычное сообщение
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=get_date_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=get_date_keyboard(),
            parse_mode='Markdown'
        )
    
    return CHOOSE_DATE

async def handle_date_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора даты"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("date_"):
        selected_date = data.replace("date_", "")
        user_data_store[user_id]['date'] = selected_date
        
        await query.edit_message_text(
            f"✅ **Выбрана дата:** {selected_date}\n\n"
            "🛣️ **Шаг 2:** Выберите направление:",
            reply_markup=get_direction_keyboard(),
            parse_mode='Markdown'
        )
        
        return CHOOSE_DIRECTION
    
    elif data == "custom_date":
        await query.edit_message_text(
            "📅 **Введите дату в формате YYYY-MM-DD**\n\n"
            "Например: `2025-01-15`\n\n"
            "Или нажмите кнопку ниже для возврата:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Выбрать из списка", callback_data="back_to_date_list")
            ]]),
            parse_mode='Markdown'
        )
        
        return CHOOSE_DATE
    
    elif data == "back_to_main":
        # Очищаем данные пользователя и выходим из конversation
        if user_id in user_data_store:
            del user_data_store[user_id]
        
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск рейсов", callback_data="search_routes")],
            [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
            [InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        
        await query.edit_message_text(
            "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
            "🛣️ **Направления:** Минск ⇄ Островец\n"
            "🌐 **Источник:** билет.маршруточка.бел\n\n"
            "💡 **Выберите действие:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    return CHOOSE_DATE

async def handle_direction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора направления"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("dir_"):
        direction = data.replace("dir_", "")
        user_data_store[user_id]['direction'] = direction
        
        direction_text = {
            "minsk_ostrovets": "Минск → Островец",
            "ostrovets_minsk": "Островец → Минск", 
            "both": "Оба направления"
        }.get(direction, direction)
        
        await query.edit_message_text(
            f"✅ **Направление:** {direction_text}\n\n"
            "⏰ **Шаг 3:** Что важнее - время отправления или прибытия?",
            reply_markup=get_time_type_keyboard(),
            parse_mode='Markdown'
        )
        
        return CHOOSE_TIME_TYPE
    
    elif data == "back_to_date":
        await query.edit_message_text(
            "🔔 **Настройка мониторинга рейсов**\n\n"
            "Я буду проверять появление мест каждые 5 минут и уведомлять вас!\n\n"
            "📅 **Шаг 1:** Выберите дату поездки:",
            reply_markup=get_date_keyboard(),
            parse_mode='Markdown'
        )
        
        return CHOOSE_DATE
    
    return CHOOSE_DIRECTION

async def handle_time_type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа времени"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("time_"):
        time_type = data.replace("time_", "")
        user_data_store[user_id]['time_type'] = time_type
        
        time_text = {
            "departure": "время отправления",
            "arrival": "время прибытия",
            "any": "любое время"
        }.get(time_type, time_type)
        
        if time_type == "any":
            # Если любое время, пропускаем выбор диапазона
            user_data_store[user_id]['time_range'] = "любое время"
            
            config_text = format_monitor_config(user_data_store[user_id])
            
            await query.edit_message_text(
                f"✅ **Настройки мониторинга:**\n\n{config_text}\n\n"
                "❓ **Запустить мониторинг?**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Да, запустить!", callback_data="confirm_yes")],
                    [InlineKeyboardButton("❌ Нет, изменить", callback_data="confirm_no")],
                    [InlineKeyboardButton("🔙 Время", callback_data="back_to_time_type")]
                ]),
                parse_mode='Markdown'
            )
            
            return CONFIRM_MONITORING
        else:
            await query.edit_message_text(
                f"✅ **Критерий:** {time_text}\n\n"
                "🕐 **Шаг 4:** Выберите желаемый диапазон времени:",
                reply_markup=get_time_range_keyboard(time_type),
                parse_mode='Markdown'
            )
            
            return CHOOSE_TIME_RANGE
    
    elif data == "back_to_direction":
        direction_text = {
            "minsk_ostrovets": "Минск → Островец",
            "ostrovets_minsk": "Островец → Минск", 
            "both": "Оба направления"
        }.get(user_data_store[user_id].get('direction', ''), user_data_store[user_id].get('direction', ''))
        
        await query.edit_message_text(
            f"✅ **Направление:** {direction_text}\n\n"
            "🛣️ **Шаг 2:** Выберите направление:",
            reply_markup=get_direction_keyboard(),
            parse_mode='Markdown'
        )
        
        return CHOOSE_DIRECTION
    
    return CHOOSE_TIME_TYPE

async def handle_time_range_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора диапазона времени"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("range_"):
        time_range = data.replace("range_", "")
        
        if time_range == "custom":
            await query.edit_message_text(
                "🕐 **Введите диапазон времени в формате ЧЧ:ММ-ЧЧ:ММ**\n\n"
                "Примеры:\n"
                "• `07:00-09:00` - с 7 до 9 утра\n"
                "• `17:30-19:30` - с 17:30 до 19:30\n\n"
                "Или нажмите кнопку ниже:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Выбрать из списка", callback_data="back_to_range_list")
                ]]),
                parse_mode='Markdown'
            )
            
            return CHOOSE_TIME_RANGE
        else:
            user_data_store[user_id]['time_range'] = time_range
            
            config_text = format_monitor_config(user_data_store[user_id])
            
            await query.edit_message_text(
                f"✅ **Настройки мониторинга:**\n\n{config_text}\n\n"
                "❓ **Запустить мониторинг?**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Да, запустить!", callback_data="confirm_yes")],
                    [InlineKeyboardButton("❌ Нет, изменить", callback_data="confirm_no")],
                    [InlineKeyboardButton("🔙 Диапазон времени", callback_data="back_to_time_range")]
                ]),
                parse_mode='Markdown'
            )
            
            return CONFIRM_MONITORING

async def handle_monitoring_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения мониторинга"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "confirm_yes":
        # Запускаем мониторинг
        config = user_data_store[user_id].copy()
        config['user_id'] = user_id
        config['chat_id'] = query.message.chat_id
        config['created_at'] = datetime.now().isoformat()
        
        active_monitors[user_id] = config
        save_active_monitors()
        
        # Добавляем задачу в планировщик
        scheduler.add_job(
            check_routes_for_user,
            'interval',
            minutes=5,
            id=f"monitor_{user_id}",
            args=[user_id],
            replace_existing=True
        )
        
        await query.edit_message_text(
            "🎉 **Мониторинг запущен!**\n\n"
            f"{format_monitor_config(config)}\n\n"
            "✅ Я буду проверять наличие мест каждые 5 минут\n"
            "📱 Уведомления придут как только появятся подходящие рейсы\n\n"
            "💡 Для управления мониторингом используйте /monitoring",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 Управление мониторингом", callback_data="manage_monitoring")
            ]]),
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    elif data == "confirm_no":
        await query.edit_message_text(
            "🔧 **Настройка мониторинга**\n\n"
            "Выберите, что хотите изменить:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Дата", callback_data="change_date")],
                [InlineKeyboardButton("🛣️ Направление", callback_data="change_direction")],
                [InlineKeyboardButton("⏰ Время", callback_data="change_time")],
                [InlineKeyboardButton("🚫 Отменить", callback_data="cancel_setup")]
            ]),
            parse_mode='Markdown'
        )

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_data_store:
        # Обычный поиск рейсов
        await handle_regular_search(update, context)
        return
    
    # Проверяем, что пользователь вводит в процессе настройки
    current_state = context.user_data.get('state')
    
    # Ввод даты
    import re
    if re.match(r'^\d{4}-\d{2}-\d{2}$', text):
        try:
            datetime.strptime(text, '%Y-%m-%d')
            user_data_store[user_id]['date'] = text
            
            await update.message.reply_text(
                f"✅ **Выбрана дата:** {text}\n\n"
                "🛣️ **Шаг 2:** Выберите направление:",
                reply_markup=get_direction_keyboard(),
                parse_mode='Markdown'
            )
            
            return CHOOSE_DIRECTION
        except ValueError:
            await update.message.reply_text(
                "❌ **Неверный формат даты**\n\n"
                "Используйте формат YYYY-MM-DD, например: `2025-01-15`",
                parse_mode='Markdown'
            )
            return CHOOSE_DATE
    
    # Ввод диапазона времени
    elif re.match(r'^\d{2}:\d{2}-\d{2}:\d{2}$', text):
        user_data_store[user_id]['time_range'] = text
        
        config_text = format_monitor_config(user_data_store[user_id])
        
        await update.message.reply_text(
            f"✅ **Настройки мониторинга:**\n\n{config_text}\n\n"
            "❓ **Запустить мониторинг?**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, запустить!", callback_data="confirm_yes")],
                [InlineKeyboardButton("❌ Нет, изменить", callback_data="confirm_no")]
            ]),
            parse_mode='Markdown'
        )
        
        return CONFIRM_MONITORING
    
    else:
        await handle_regular_search(update, context)

# ==================== MONITORING FUNCTIONS ====================

async def check_routes_for_user(user_id: int):
    """Проверка рейсов для конкретного пользователя"""
    if user_id not in active_monitors:
        return
    
    config = active_monitors[user_id]
    
    try:
        await init_parser()
        
        # Получаем все рейсы на дату
        routes_data = await parser.get_all_routes(config['date'])
        
        if not routes_data.get('success', False):
            return
        
        # Фильтруем рейсы по критериям
        suitable_routes = filter_routes_by_criteria(routes_data, config)
        
        if suitable_routes:
            await send_monitoring_notification(user_id, suitable_routes, config)
    
    except Exception as e:
        logger.error(f"Ошибка при проверке рейсов для пользователя {user_id}: {e}")

def filter_routes_by_criteria(routes_data, config):
    """Фильтрация рейсов по критериям пользователя"""
    suitable_routes = []
    
    # Определяем, какие маршруты проверять
    routes_to_check = []
    if config['direction'] in ['minsk_ostrovets', 'both']:
        routes_to_check.extend(routes_data.get('minsk_to_ostrovets', []))
    if config['direction'] in ['ostrovets_minsk', 'both']:
        routes_to_check.extend(routes_data.get('ostrovets_to_minsk', []))
    
    for route in routes_to_check:
        # Проверяем наличие мест
        seats = route.get('available_seats', 0)
        if not isinstance(seats, int) or seats <= 0:
            continue
        
        # Проверяем время, если задан диапазон
        if config['time_range'] != 'any' and config['time_range'] != 'любое время':
            if not check_time_criteria(route, config):
                continue
        
        suitable_routes.append(route)
    
    return suitable_routes

def check_time_criteria(route, config):
    """Проверка соответствия времени критериям"""
    time_range = config['time_range']
    time_type = config['time_type']
    
    # Получаем нужное время из рейса
    if time_type == 'departure':
        route_time = route.get('departure_time', '')
    elif time_type == 'arrival':
        route_time = route.get('arrival_time', '')
    else:
        return True  # Любое время
    
    if not route_time:
        return False
    
    try:
        # Парсим время рейса
        route_hour, route_minute = map(int, route_time.split(':'))
        route_minutes = route_hour * 60 + route_minute
        
        # Парсим диапазон
        if '-' in time_range:
            start_time, end_time = time_range.split('-')
            start_hour, start_minute = map(int, start_time.split(':'))
            end_hour, end_minute = map(int, end_time.split(':'))
            
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute
            
            # Проверяем попадание в диапазон
            if start_minutes <= end_minutes:
                return start_minutes <= route_minutes <= end_minutes
            else:
                # Диапазон через полночь
                return route_minutes >= start_minutes or route_minutes <= end_minutes
    
    except ValueError:
        return True
    
    return True

async def send_monitoring_notification(user_id: int, routes: List, config: Dict):
    """Отправка уведомления о найденных рейсах"""
    try:
        from telegram import Bot
        
        bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        chat_id = config['chat_id']
        
        direction_text = {
            "minsk_ostrovets": "Минск → Островец",
            "ostrovets_minsk": "Островец → Минск",
            "both": "в обоих направлениях"
        }.get(config['direction'], config['direction'])
        
        message_parts = [
            "🔔 **НАЙДЕНЫ ПОДХОДЯЩИЕ РЕЙСЫ!**",
            "",
            f"📅 **Дата:** {config['date']}",
            f"🛣️ **Направление:** {direction_text}",
            f"⏰ **Время:** {config['time_range']}",
            ""
        ]
        
        for i, route in enumerate(routes[:5], 1):  # Показываем до 5 рейсов
            seats = route.get('available_seats', 0)
            emoji = "🔥" if seats <= 3 else "✅"
            direction = f"{route['from_city']} → {route['to_city']}"
            
            message_parts.append(f"**{i}. {direction}**")
            message_parts.append(f"🚀 {route.get('departure_time')} → 🎯 {route.get('arrival_time')}")
            message_parts.append(f"{emoji} **{seats} мест** | {route.get('carrier', 'н/д')}")
            message_parts.append("")
        
        if len(routes) > 5:
            message_parts.append(f"... и еще {len(routes) - 5} рейсов")
        
        message_parts.extend([
            "",
            "💡 Для бронирования перейдите на сайт билет.маршруточка.бел",
            "",
            "🔄 Мониторинг продолжается..."
        ])
        
        message = "\n".join(message_parts)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛑 Остановить мониторинг", callback_data="stop_monitoring")],
            [InlineKeyboardButton("📊 Управление", callback_data="manage_monitoring")]
        ])
        
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")

# ==================== REGULAR COMMANDS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск рейсов", callback_data="search_routes")],
        [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
        [InlineKeyboardButton("� Войти в аккаунт", callback_data="login_account")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="view_profile")],
        [InlineKeyboardButton("�📊 Мои мониторинги", callback_data="my_monitors")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    
    await update.message.reply_text(
        "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
        "🛣️ **Направления:** Минск ⇄ Островец\n"
        "🌐 **Источник:** билет.маршруточка.бел\n\n"
        "🆕 **Новые возможности:**\n"
        "• 🔐 Вход в личный кабинет\n"
        "• 👤 Просмотр профиля\n"
        "• 🎫 Управление бронями\n"
        "• 🔍 Расширенный поиск\n\n"
        "💡 **Выберите действие:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
    
    await update.message.reply_text(
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
        "• `/check_booking` - статус бронирования\n"
        "• `/help` - эта справка\n\n"
        "🚌 **Направления:**\n"
        "• Минск → Островец\n"
        "• Островец → Минск",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def monitoring_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /monitoring"""
    user_id = update.effective_user.id
    
    if user_id in active_monitors:
        config = active_monitors[user_id]
        config_text = format_monitor_config(config)
        
        keyboard = [
            [InlineKeyboardButton("🛑 Остановить", callback_data="stop_monitoring")],
            [InlineKeyboardButton("🔧 Изменить", callback_data="setup_monitoring")],
            [InlineKeyboardButton("📱 Проверить сейчас", callback_data="check_now")]
        ]
        
        await update.message.reply_text(
            f"📊 **Активный мониторинг:**\n\n{config_text}\n\n"
            f"⏰ **Создан:** {config.get('created_at', 'н/д')[:19].replace('T', ' ')}\n\n"
            "💡 **Действия:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        keyboard = [[InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")]]
        
        await update.message.reply_text(
            "📊 **Мониторинг не активен**\n\n"
            "💡 Хотите настроить автоматическую проверку рейсов?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def handle_regular_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обычный поиск рейсов по дате"""
    text = update.message.text.strip()
    
    import re
    if re.match(r'^\d{4}-\d{2}-\d{2}$', text):
        try:
            datetime.strptime(text, '%Y-%m-%d')
            await update.message.reply_text(f"🔍 **Ищу рейсы на {text}...**", parse_mode='Markdown')
            
            await init_parser()
            routes_data = await parser.get_all_routes(text)
            message = format_routes_message(routes_data, text)
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text("❌ **Ошибка поиска**", parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "💡 Отправьте дату в формате **YYYY-MM-DD** или используйте /help",
            parse_mode='Markdown'
        )

def format_routes_message(routes_data, date):
    """Форматирование сообщения с рейсами"""
    if not routes_data.get('success', False):
        return "❌ **Не удалось получить данные**"
    
    minsk_routes = routes_data.get('minsk_to_ostrovets', [])[:8]
    ostrovets_routes = routes_data.get('ostrovets_to_minsk', [])[:8]
    
    parts = [f"📅 **Рейсы на {date}**", ""]
    
    if minsk_routes:
        parts.append("🚌 **Минск → Островец:**")
        for i, route in enumerate(minsk_routes, 1):
            seats = route.get('available_seats', 0)
            emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
            parts.append(f"{i}. **{route.get('departure_time')} → {route.get('arrival_time')}** ({route.get('duration', 'н/д')})")
            parts.append(f"   {emoji} {seats} мест | {route.get('carrier', 'н/д')}")
        parts.append("")
    
    if ostrovets_routes:
        parts.append("🚌 **Островец → Минск:**")
        for i, route in enumerate(ostrovets_routes, 1):
            seats = route.get('available_seats', 0)
            emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
            parts.append(f"{i}. **{route.get('departure_time')} → {route.get('arrival_time')}** ({route.get('duration', 'н/д')})")
            parts.append(f"   {emoji} {seats} мест | {route.get('carrier', 'н/д')}")
    
    total = len(routes_data.get('minsk_to_ostrovets', [])) + len(routes_data.get('ostrovets_to_minsk', []))
    parts.append(f"\n📊 **Всего рейсов:** {total}")
    
    return "\n".join(parts)

# ==================== CALLBACK HANDLERS ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общий обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "setup_monitoring":
        # Начинаем настройку мониторинга
        user_data_store[user_id] = {}
        
        await query.edit_message_text(
            "🔔 **Настройка мониторинга рейсов**\n\n"
            "Я буду проверять появление мест каждые 5 минут и уведомлять вас!\n\n"
            "📅 **Шаг 1:** Выберите дату поездки:",
            reply_markup=get_date_keyboard(),
            parse_mode='Markdown'
        )
        
        return CHOOSE_DATE
    
    elif data == "stop_monitoring":
        if user_id in active_monitors:
            del active_monitors[user_id]
            save_active_monitors()
            
            # Удаляем задачу из планировщика
            try:
                scheduler.remove_job(f"monitor_{user_id}")
            except:
                pass
            
            await query.edit_message_text(
                "✅ **Мониторинг остановлен**\n\n"
                "💡 Для настройки нового мониторинга используйте /start",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "ℹ️ **Мониторинг не был активен**",
                parse_mode='Markdown'
            )
    
    elif data == "search_routes":
        await query.edit_message_text(
            "🔍 **Поиск рейсов**\n\n"
            "📅 Выберите дату для поиска:",
            reply_markup=get_date_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data.startswith("date_") and user_id not in user_data_store:
        # Обычный поиск по дате
        selected_date = data.replace("date_", "")
        await query.edit_message_text(f"🔍 **Ищу рейсы на {selected_date}...**", parse_mode='Markdown')
        
        try:
            await init_parser()
            routes_data = await parser.get_all_routes(selected_date)
            message = format_routes_message(routes_data, selected_date)
            
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            await query.edit_message_text("❌ **Ошибка при поиске рейсов**", parse_mode='Markdown')
    
    elif data == "back_to_main":
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск рейсов", callback_data="search_routes")],
            [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
            [InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        
        await query.edit_message_text(
            "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
            "🛣️ **Направления:** Минск ⇄ Островец\n"
            "🌐 **Источник:** билет.маршруточка.бел\n\n"
            "💡 **Выберите действие:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "help":
        await query.edit_message_text(
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
            "• `/help` - эта справка\n\n"
            "🚌 **Направления:**\n"
            "• Минск → Островец\n"
            "• Островец → Минск",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
            ]]),
            parse_mode='Markdown'
        )
    
    elif data == "my_monitors":
        if user_id in active_monitors:
            config = active_monitors[user_id]
            config_text = format_monitor_config(config)
            
            keyboard = [
                [InlineKeyboardButton("🛑 Остановить", callback_data="stop_monitoring")],
                [InlineKeyboardButton("🔧 Изменить", callback_data="setup_monitoring")],
                [InlineKeyboardButton("📱 Проверить сейчас", callback_data="check_now")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
            ]
            
            await query.edit_message_text(
                f"📊 **Активный мониторинг:**\n\n{config_text}\n\n"
                f"⏰ **Создан:** {config.get('created_at', 'н/д')[:19].replace('T', ' ')}\n\n"
                "💡 **Действия:**",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
            ]
            
            await query.edit_message_text(
                "📊 **Мониторинг не активен**\n\n"
                "💡 Хотите настроить автоматическую проверку рейсов?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    elif data == "check_now":
        if user_id in active_monitors:
            await query.answer("🔍 Проверяю рейсы...")
            await check_routes_for_user(user_id)
            await query.edit_message_text(
                "✅ **Проверка завершена**\n\n"
                "Если найдены подходящие рейсы, вы получите уведомление.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                ]]),
                parse_mode='Markdown'
            )
        else:
            await query.answer("❌ Мониторинг не активен")
    
    else:
        await query.answer("❓ Неизвестная команда")

# ==================== PROFILE AND BOOKING COMMANDS ====================

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для входа в аккаунт"""
    user_id = update.effective_user.id
    
    if user_id in user_auth and user_auth[user_id].get('authenticated'):
        await update.message.reply_text(
            "✅ **Вы уже авторизованы в системе!**\n\n"
            "🔍 Используйте /profile для просмотра профиля\n"
            "🎫 Используйте /bookings для просмотра броней",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔐 **Вход в аккаунт маршруточки**\n\n"
        "📱 Введите ваш номер телефона в формате +375XXXXXXXXX:",
        parse_mode='Markdown'
    )
    
    return LOGIN_PHONE

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра профиля"""
    user_id = update.effective_user.id
    
    if user_id not in user_auth or not user_auth[user_id].get('authenticated'):
        await update.message.reply_text(
            "🔐 **Для просмотра профиля требуется авторизация**\n\n"
            "💡 Используйте /login для входа в аккаунт",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "⏳ **Загружаю информацию профиля...**",
        parse_mode='Markdown'
    )
    
    try:
        await init_auth_manager()
        profile_info = await auth_manager.get_profile_info()
        
        try:
            from .ticket_formatter import TicketFormatter
        except ImportError:
            from ticket_formatter import TicketFormatter
        
        formatted_profile = TicketFormatter.format_profile_info(profile_info)
        
        keyboard = [
            [InlineKeyboardButton("🎫 Мои брони", callback_data="view_bookings")],
            [InlineKeyboardButton("🔍 Поиск рейсов", callback_data="search_routes")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_profile")]
        ]
        
        await update.message.reply_text(
            formatted_profile,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении профиля для пользователя {user_id}: {e}")
        await update.message.reply_text(
            "❌ **Ошибка загрузки профиля**\n\n"
            "⚠️ Попробуйте позже или переавторизуйтесь",
            parse_mode='Markdown'
        )

async def bookings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра бронирований"""
    user_id = update.effective_user.id
    
    if user_id not in user_auth or not user_auth[user_id].get('authenticated'):
        await update.message.reply_text(
            "🔐 **Для просмотра броней требуется авторизация**\n\n"
            "💡 Используйте /login для входа в аккаунт",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "⏳ **Загружаю ваши бронирования...**",
        parse_mode='Markdown'
    )
    
    try:
        await init_auth_manager()
        bookings = await auth_manager.get_bookings()
        
        try:
            from .ticket_formatter import TicketFormatter
        except ImportError:
            from ticket_formatter import TicketFormatter
        
        formatted_bookings = TicketFormatter.format_booking_list(bookings)
        
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск рейсов", callback_data="search_routes")],
            [InlineKeyboardButton("👤 Профиль", callback_data="view_profile")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_bookings")]
        ]
        
        await update.message.reply_text(
            formatted_bookings,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Ошибка при получении броней для пользователя {user_id}: {e}")
        await update.message.reply_text(
            "❌ **Ошибка загрузки броней**\n\n"
            "⚠️ Попробуйте позже или переавторизуйтесь",
            parse_mode='Markdown'
        )

async def check_booking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка статуса бронирования"""
    await update.message.reply_text(
        "📋 **Проверка бронирования**\n\n"
        "Введите номер бронирования:",
        parse_mode='Markdown'
    )

    return BOOKING_NUMBER

async def handle_booking_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение номера бронирования"""
    context.user_data['booking_number'] = update.message.text.strip()

    await update.message.reply_text(
        "📱 **Последние 4 цифры телефона?**\n"
        "Если не помните, отправьте `-`",
        parse_mode='Markdown'
    )

    return PHONE_DIGITS

async def handle_phone_digits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение последних цифр телефона и вывод статуса"""
    phone_digits = update.message.text.strip()
    if phone_digits in {'-', 'нет', 'Нет', 'skip', 'Skip'}:
        phone_digits = None

    booking_number = context.user_data.get('booking_number')

    await update.message.reply_text(
        "⏳ **Проверяю бронирование...**",
        parse_mode='Markdown'
    )

    try:
        await init_auth_manager()
        status = await auth_manager.check_booking_status(booking_number, phone_digits)

        try:
            from .ticket_formatter import TicketFormatter
        except ImportError:
            from ticket_formatter import TicketFormatter

        formatted_status = TicketFormatter.format_booking_status(status)
        await update.message.reply_text(formatted_status, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка при проверке брони {booking_number}: {e}")
        await update.message.reply_text(
            "❌ **Ошибка при проверке бронирования**",
            parse_mode='Markdown'
        )

    return ConversationHandler.END

# ==================== MAIN FUNCTION ====================

async def post_init(application):
    """Инициализация после запуска приложения"""
    global scheduler
    scheduler.start()
    # Восстанавливаем задачи мониторинга из сохранённого файла
    for uid in list(active_monitors.keys()):
        scheduler.add_job(
            check_routes_for_user,
            'interval',
            minutes=5,
            id=f"monitor_{uid}",
            args=[uid],
            replace_existing=True
        )
    print("✅ Планировщик запущен!")

def main():
    """Главная функция"""
    print("🚀 Запуск продвинутого бота")
    print("📱 @MarshrutochkaOst_bot")
    print("🔔 Функции мониторинга включены")
    print("=" * 50)
    
    # Создание приложения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ Не найден токен TELEGRAM_BOT_TOKEN")
        return
    
    app = Application.builder().token(token).post_init(post_init).build()

    # Настройка ConversationHandler для мониторинга
    monitoring_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_monitoring_conversation, pattern="^setup_monitoring$"),
            CommandHandler("monitor", start_monitoring_conversation)
        ],
        states={
            CHOOSE_DATE: [
                CallbackQueryHandler(handle_date_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input)
            ],
            CHOOSE_DIRECTION: [
                CallbackQueryHandler(handle_direction_choice)
            ],
            CHOOSE_TIME_TYPE: [
                CallbackQueryHandler(handle_time_type_choice)
            ],
            CHOOSE_TIME_RANGE: [
                CallbackQueryHandler(handle_time_range_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input)
            ],
            CONFIRM_MONITORING: [
                CallbackQueryHandler(handle_monitoring_confirmation)
            ]
        },
        per_user=True,
        fallbacks=[
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^cancel")
        ]
    )

    check_booking_handler = ConversationHandler(
        entry_points=[CommandHandler("check_booking", check_booking_command)],
        states={
            BOOKING_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_booking_number)],
            PHONE_DIGITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_digits)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        per_user=True,
    )

    # Добавление обработчиков
    app.add_handler(monitoring_handler)
    app.add_handler(check_booking_handler)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("bookings", bookings_command))
    app.add_handler(CommandHandler("monitoring", monitoring_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    app.add_error_handler(error_handler)
    
    print("✅ Бот готов к запуску!")
    print("💬 Напишите /start для начала")
    print("🔔 Мониторинг каждые 5 минут")
    print("⛔ Ctrl+C для остановки")
    print("=" * 50)
    
    # Запуск
    try:
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\n👋 Остановка бота...")
    except Conflict:
        print("💥 Бот уже запущен в другом месте")
    except Exception as e:
        print(f"💥 Ошибка: {e}")
    finally:
        try:
            scheduler.shutdown()
        except:
            pass
        print("✅ Бот остановлен")

if __name__ == "__main__":
    main()
