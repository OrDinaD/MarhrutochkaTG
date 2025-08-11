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
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
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

# Импортируем модули с новой структурой
try:
    from .auth import RequestsAuthManager, bot_auth_manager, format_profile_message, format_bookings_message
    from .utils import FinalMarshrutochkaParser, AutoBookingManager
    from .monitoring import setup_logging, railway_logger, crash_handler, diagnostic_system, auto_recovery
    from .admin_panel import AdminPanel
    from .security import security
except ImportError:
    from auth import RequestsAuthManager, bot_auth_manager, format_profile_message, format_bookings_message
    from utils import FinalMarshrutochkaParser, AutoBookingManager
    from monitoring import setup_logging, railway_logger, crash_handler, diagnostic_system, auto_recovery
    from admin_panel import AdminPanel
    from security import security

# Настройка логирования - используем Railway enhanced logger если доступен
if railway_logger:
    logger = railway_logger
    is_railway_logger = True
else:
    logger = setup_logging(logging.INFO)
    is_railway_logger = False

# Определяем, используем ли мы Railway logger
try:
    from .railway_logger import RailwayLogger
    is_railway_logger = is_railway_logger or isinstance(logger, RailwayLogger)
except ImportError:
    pass

# Игнорируем предупреждения от python-telegram-bot о per_message
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=PTBUserWarning)

# Отключаем подробные сообщения от httpx, используемого библиотекой telegram
logging.getLogger("httpx").setLevel(logging.WARNING)

# Состояния для ConversationHandler
(CHOOSE_DATE, CHOOSE_DIRECTION, CHOOSE_TIME_TYPE, CHOOSE_TIME_RANGE, 
 CONFIRM_MONITORING, MONITORING_ACTIVE, LOGIN_PHONE, LOGIN_PASSWORD,
 SEARCH_FROM, SEARCH_TO, SEARCH_DATE, BOOKING_NUMBER, PHONE_DIGITS,
 LOGIN_REQUESTS_PHONE, LOGIN_REQUESTS_PASSWORD, CHOOSE_PASSENGER_COUNT,
 CONFIRM_BOOKING, ADMIN_SEARCH_USER) = range(18)

# Глобальные переменные
parser = None
requests_auth_manager = None # Для нового менеджера
job_queue = None  # Встроенная очередь заданий PTB
active_monitors = {}  # user_id -> monitor_config
user_data_store = {}  # user_id -> user_data
application = None  # will hold the Application instance
admin_panel = None  # Административная панель

# Создаем директории для данных
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'user_sessions'), exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, 'monitors.json')
# Хранилище сессий (для legacy авторизации через RequestsAuthManager)
user_sessions = {}
USER_SESSIONS_FILE = os.path.join(DATA_DIR, 'user_sessions.json')

def load_user_sessions():
    """Загрузка сессий пользователей из файла (legacy RequestsAuthManager)."""
    global user_sessions
    if os.path.exists(USER_SESSIONS_FILE):
        try:
            with open(USER_SESSIONS_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            # Нельзя напрямую восстановить requests.Session; сохраняем только метаданные.
            # Поэтому при необходимости авторизации заново пользователь выполнит вход.
            if isinstance(raw, dict):
                user_sessions = raw
            logger.info(f"🔓 Загружены legacy-сессии (метаданные) для {len(user_sessions)} пользователей")
        except Exception as e:
            logger.error(f"Не удалось загрузить user_sessions: {e}")

def save_user_sessions():
    """Сохранение метаданных сессий пользователей (legacy)."""
    try:
        with open(USER_SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_sessions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Не удалось сохранить user_sessions: {e}")

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

# НЕ загружаем мониторинги на уровне модуля - переносим в main()
# load_active_monitors()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors from telegram.ext and log them."""
    if is_railway_logger:
        # Получаем дополнительную информацию об update
        update_info = {}
        if hasattr(update, 'effective_user') and update.effective_user:
            update_info['user_id'] = update.effective_user.id
        if hasattr(update, 'effective_chat') and update.effective_chat:
            update_info['chat_id'] = update.effective_chat.id
        if hasattr(update, 'effective_message') and update.effective_message:
            update_info['message_id'] = update.effective_message.message_id
            
        logger.bot_action("Ошибка при обработке update", update_info, level="error")
        logger.error("Exception details:", exc_info=context.error)
    else:
        logger.error("Exception while handling an update:", exc_info=context.error)

async def init_parser():
    """Инициализация парсера"""
    global parser
    if parser is None:
        parser = FinalMarshrutochkaParser()
        await parser.__aenter__()

async def init_requests_auth_manager():
    """Инициализация менеджера аутентификации через Requests"""
    global requests_auth_manager
    if requests_auth_manager is None:
        requests_auth_manager = RequestsAuthManager()
        # Здесь не нужен асинхронный вход, т.к. класс синхронный

# ==================== UTILITY FUNCTIONS ====================

def create_webapp_url(direction: str, date: str = None) -> str:
    """Создает URL для веб-приложения маршруточки с предвыбранным направлением"""
    # Используем главную страницу сайта вместо API endpoint
    base_url = "https://билет.маршруточка.бел/"
    
    # Возвращаем просто главную страницу - пользователь сам выберет направление и дату
    # Это проще и надежнее чем пытаться угадать API параметры
    return base_url

def create_webapp_keyboard(direction: str = None, date: str = None, additional_buttons: list = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками веб-приложений"""
    keyboard = []
    
    if direction:
        # Создаем кнопку для конкретного направления
        direction_names = {
            "minsk_ostrovets": "🏙️ Минск → Островец",
            "ostrovets_minsk": "🏘️ Островец → Минск",
            "both": "🔄 Оба направления"
        }
        
        if direction in ["minsk_ostrovets", "ostrovets_minsk"]:
            webapp_url = create_webapp_url(direction, date)
            web_app = WebAppInfo(url=webapp_url)
            keyboard.append([
                InlineKeyboardButton(
                    f"🌐 Открыть сайт бронирования", 
                    web_app=web_app
                )
            ])
        elif direction == "both":
            # Добавляем кнопки для обоих направлений
            webapp_url = create_webapp_url("both", date)
            
            keyboard.extend([
                [InlineKeyboardButton("🚌 Открыть сайт маршруточки", web_app=WebAppInfo(url=webapp_url))]
            ])
    else:
        # Создаем кнопку для общего доступа к сайту
        webapp_url = create_webapp_url("general", date)
        
        keyboard.extend([
            [InlineKeyboardButton("🚌 Открыть сайт маршруточки", web_app=WebAppInfo(url=webapp_url))]
        ])
    
    # Добавляем дополнительные кнопки если есть
    if additional_buttons:
        keyboard.extend(additional_buttons)
    
    return InlineKeyboardMarkup(keyboard)

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

def get_main_menu_keyboard(user_id: int):
    """Возвращает клавиатуру главного меню в зависимости от статуса аутентификации."""
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск рейсов", callback_data="search_routes")],
        [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
        [InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors")]
    ]

    if bot_auth_manager.is_authenticated(user_id):
        # Пользователь вошел через улучшенную систему авторизации
        keyboard.extend([
            [InlineKeyboardButton("👤 Мой профиль", callback_data="profile_requests")],
            [InlineKeyboardButton("🎫 Мои бронирования", callback_data="tickets_requests")],
            [InlineKeyboardButton("🤖 Автобронирование", callback_data="auto_booking")],
            [InlineKeyboardButton("🚪 Выйти из аккаунта", callback_data="logout_requests")]
        ])
    else:
        # Пользователь не вошел
        keyboard.append([InlineKeyboardButton("🔒 Войти в аккаунт", callback_data="login_requests")])

    # Добавляем админ-панель для администратора
    if admin_panel and admin_panel.is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Функции администратора", callback_data="admin_panel")])

    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data="help")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start"""
    text = (
        "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
        "🛣️ **Направления:** Минск ⇄ Островец\n"
        "🌐 **Источник:** билет.маршруточка.бел\n\n"
        "💡 **Выберите действие:**"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_main_menu_keyboard(update.effective_user.id),
        parse_mode='Markdown'
    )

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    text = (
        "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
        "🛣️ **Направления:** Минск ⇄ Островец\n"
        "🌐 **Источник:** билет.маршруточка.бел\n\n"
        "💡 **Выберите действие:**"
    )

    await query.edit_message_text(
        text,
        reply_markup=get_main_menu_keyboard(user_id),
        parse_mode='Markdown'
    )

async def my_monitors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать мои мониторинги"""
    user_id = update.effective_user.id
    
    if user_id in active_monitors:
        config = active_monitors[user_id]
        config_text = format_monitor_config(config)
        
        keyboard = [
            [InlineKeyboardButton("🛑 Остановить", callback_data="stop_monitoring")],
            [InlineKeyboardButton("🔧 Изменить", callback_data="setup_monitoring")],
            [InlineKeyboardButton("📱 Проверить сейчас", callback_data="check_now")]
        ]
        
        message_text = (
            f"📊 **Активный мониторинг:**\n\n{config_text}\n\n"
            f"⏰ **Создан:** {config.get('created_at', 'н/д')[:19].replace('T', ' ')}\n\n"
            "💡 **Действия:**"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    else:
        keyboard = [
            [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ]
        
        message_text = (
            "📊 **Мониторинг не активен**\n\n"
            "💡 Хотите настроить автоматическую проверку рейсов?"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановить мониторинг"""
    user_id = update.effective_user.id
    
    if user_id in active_monitors:
        del active_monitors[user_id]
        save_active_monitors()
        
        # Удаляем задачу из планировщика
        try:
            if job_queue:
                # Удаляем существующие задания
                current_jobs = job_queue.get_jobs_by_name(f"monitor_{user_id}")
                for job in current_jobs:
                    job.schedule_removal()
        except:
            pass
        
        message_text = (
            "✅ **Мониторинг остановлен**\n\n"
            "💡 Для настройки нового мониторинга используйте /start"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message_text,
                parse_mode='Markdown'
            )
    else:
        message_text = "ℹ️ **Мониторинг не был активен**"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message_text,
                parse_mode='Markdown'
            )

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

async def start_login_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса входа через улучшенную систему авторизации"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="🔐 **ВХОД В АККАУНТ МАРШРУТОЧКИ**\n\n"
        "📱 Введите ваш номер телефона в формате:\n"
        "`+375XXXXXXXXX` или `375XXXXXXXXX`\n\n"
        "💡 Пример: +375291234567",
        parse_mode='Markdown'
    )
    return LOGIN_REQUESTS_PHONE

async def handle_phone_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода телефона для входа"""
    phone = security.sanitize_input(update.message.text, max_length=20)
    user_id = update.effective_user.id
    
    # Валидация номера
    if not security.validate_phone(phone):
        security.log_security_event("invalid_phone_format", user_id, {"phone": phone})
        await update.message.reply_text(
            "❌ **Неверный формат номера**\n\n"
            "Введите номер в формате: `+375XXXXXXXXX`",
            parse_mode='Markdown'
        )
        return LOGIN_REQUESTS_PHONE
    
    context.user_data['phone'] = phone
    
    await update.message.reply_text(
        "🔑 **Введите пароль от аккаунта:**",
        parse_mode='Markdown'
    )
    return LOGIN_REQUESTS_PASSWORD

async def handle_password_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пароля и выполнение авторизации"""
    password = security.sanitize_input(update.message.text)
    user_id = update.effective_user.id
    phone = context.user_data.get('phone')

    if not phone:
        await update.message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте снова с /start."
        )
        return ConversationHandler.END

    # Показываем прогресс
    progress_message = await update.message.reply_text(
        "⏳ **Выполняю вход...**\n\n"
        "🔄 Проверяю данные на сервере...",
        parse_mode='Markdown'
    )

    try:
        # Выполняем авторизацию через новый менеджер
        success = bot_auth_manager.login(user_id, phone, password)

        if success:
            await progress_message.edit_text(
                "🎉 **ВХОД ВЫПОЛНЕН УСПЕШНО!**\n\n"
                "✅ Теперь вы можете:\n"
                "• 👤 Просматривать свой профиль\n"
                "• 🎫 Управлять бронированиями\n"
                "• 🤖 Использовать автобронирование\n"
                "• 🚪 Выйти из аккаунта\n\n"
                "💡 Ваша сессия сохранена и автоматически восстановится при перезапуске бота.",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )
            if is_railway_logger:
                logger.auth_action(f"Пользователь {user_id} успешно авторизован", {
                    "user_id": user_id,
                    "auth_method": "requests_auth",
                    "status": "success"
                })
            else:
                logger.info(f"Пользователь {user_id} авторизован через новую систему")
        else:
            await progress_message.edit_text(
                "❌ **ОШИБКА ВХОДА**\n\n"
                "Возможные причины:\n"
                "• Неверный номер телефона или пароль\n"
                "• Проблемы с подключением к серверу\n"
                "• Аккаунт заблокирован\n\n"
                "💡 Проверьте данные и попробуйте снова.",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )
            if is_railway_logger:
                logger.auth_action(f"Неуспешная авторизация пользователя {user_id}", {
                    "user_id": user_id,
                    "auth_method": "requests_auth",
                    "status": "failed",
                    "reason": "invalid_credentials"
                })
            else:
                logger.warning(f"Неуспешная авторизация пользователя {user_id}")
    
    except Exception as e:
        if is_railway_logger:
            logger.auth_action(f"Ошибка авторизации пользователя {user_id}", {
                "user_id": user_id,
                "auth_method": "requests_auth",
                "status": "error",
                "error": str(e)
            }, level="error")
        else:
            logger.error(f"Ошибка авторизации пользователя {user_id}: {e}")
        await progress_message.edit_text(
            "❌ **СИСТЕМНАЯ ОШИБКА**\n\n"
            "Произошла непредвиденная ошибка при входе.\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    # Очищаем временные данные
    if 'phone' in context.user_data:
        del context.user_data['phone']
    
    return ConversationHandler.END

async def get_profile_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение профиля пользователя через улучшенную систему авторизации"""
    user_id = update.effective_user.id
    
    if not bot_auth_manager.is_authenticated(user_id):
        if update.callback_query:
            await update.callback_query.answer("❌ Сначала нужно войти в аккаунт!", show_alert=True)
            await update.callback_query.edit_message_text(
                "🔒 **Доступ запрещен**\n\n"
                "Для просмотра профиля необходимо войти в аккаунт.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔒 Войти в аккаунт", callback_data="login_requests"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                ]]),
                parse_mode='Markdown'
            )
        return

    if update.callback_query:
        await update.callback_query.answer("📋 Загружаю профиль...")

    try:
        # Получаем профиль через новый менеджер
        profile = bot_auth_manager.get_user_profile(user_id)
        
        if profile:
            profile_text = format_profile_message(profile)
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="profile_requests")],
                [InlineKeyboardButton("🎫 Мои бронирования", callback_data="tickets_requests")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
            ]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    profile_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    profile_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        else:
            error_text = (
                "❌ **Не удалось загрузить профиль**\n\n"
                "Возможные причины:\n"
                "• Сессия истекла\n"
                "• Проблемы с подключением\n"
                "• Ошибка сервера\n\n"
                "💡 Попробуйте войти заново."
            )
            
            keyboard = [
                [InlineKeyboardButton("🔒 Войти заново", callback_data="login_requests")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
            ]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    error_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    error_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
    
    except Exception as e:
        logger.error(f"Ошибка при получении профиля пользователя {user_id}: {e}")
        error_text = "❌ **Системная ошибка при загрузке профиля**\n\nПопробуйте позже."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Повторить", callback_data="profile_requests")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                error_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                error_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

async def get_tickets_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение бронирований пользователя через улучшенную систему авторизации"""
    user_id = update.effective_user.id
    
    if not bot_auth_manager.is_authenticated(user_id):
        if update.callback_query:
            await update.callback_query.answer("❌ Сначала нужно войти в аккаунт!", show_alert=True)
            await update.callback_query.edit_message_text(
                "🔒 **Доступ запрещен**\n\n"
                "Для просмотра бронирований необходимо войти в аккаунт.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔒 Войти в аккаунт", callback_data="login_requests"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                ]]),
                parse_mode='Markdown'
            )
        return

    if update.callback_query:
        await update.callback_query.answer("🎫 Загружаю бронирования...")

    try:
        # Получаем бронирования через новый менеджер
        upcoming_bookings = bot_auth_manager.get_user_bookings(user_id, "upcoming")
        
        # Форматируем сообщение
        message_text = format_bookings_message(upcoming_bookings, "upcoming")
        
        # Создаем клавиатуру с дополнительными опциями
        keyboard = [
            [
                InlineKeyboardButton("📅 Предстоящие", callback_data="bookings_upcoming"),
                InlineKeyboardButton("✅ Выполненные", callback_data="bookings_completed")
            ],
            [
                InlineKeyboardButton("❌ Отмененные", callback_data="bookings_cancelled"),
                InlineKeyboardButton("🔄 Обновить", callback_data="tickets_requests")
            ],
            [
                InlineKeyboardButton("👤 Профиль", callback_data="profile_requests"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
            ]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    except Exception as e:
        logger.error(f"Ошибка при получении бронирований пользователя {user_id}: {e}")
        error_text = "❌ **Системная ошибка при загрузке бронирований**\n\nПопробуйте позже."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Повторить", callback_data="tickets_requests")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                error_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                error_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

async def logout_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из аккаунта через улучшенную систему авторизации"""
    user_id = update.effective_user.id
    
    if bot_auth_manager.is_authenticated(user_id):
        # Выполняем выход через менеджер
        success = bot_auth_manager.logout(user_id)
        
        if success:
            if update.callback_query:
                await update.callback_query.answer("✅ Выход выполнен")
                await update.callback_query.edit_message_text(
                    "🚪 **ВЫХОД ВЫПОЛНЕН УСПЕШНО!**\n\n"
                    "✅ Вы вышли из аккаунта\n"
                    "🗑️ Сессия удалена\n"
                    "🔒 Данные очищены\n\n"
                    "💡 Чтобы снова войти в аккаунт, используйте кнопку \"🔒 Войти в аккаунт\"",
                    reply_markup=get_main_menu_keyboard(user_id),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "🚪 **ВЫХОД ВЫПОЛНЕН УСПЕШНО!**\n\n"
                    "💡 Чтобы снова войти в аккаунт, используйте кнопку \"🔒 Войти в аккаунт\"",
                    reply_markup=get_main_menu_keyboard(user_id),
                    parse_mode='Markdown'
                )
            logger.info(f"Пользователь {user_id} вышел из аккаунта")
        else:
            if update.callback_query:
                await update.callback_query.answer("❌ Ошибка при выходе", show_alert=True)
            logger.error(f"Ошибка при выходе пользователя {user_id}")
    else:
        if update.callback_query:
            await update.callback_query.answer("❌ Вы не были авторизованы", show_alert=True)
            await update.callback_query.edit_message_text(
                "ℹ️ **Вы не были авторизованы в системе**\n\n"
                "💡 Используйте кнопку \"🔒 Войти в аккаунт\" для входа",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )

async def handle_bookings_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фильтрации бронирований по статусу"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if not bot_auth_manager.is_authenticated(user_id):
        await query.answer("❌ Сначала нужно войти в аккаунт!", show_alert=True)
        return
    
    # Определяем тип фильтра из callback_data
    filter_type = query.data.split('_')[1]  # bookings_upcoming -> upcoming
    
    await query.answer(f"📋 Загружаю {filter_type} бронирования...")
    
    try:
        # Получаем бронирования нужного типа
        bookings = bot_auth_manager.get_user_bookings(user_id, filter_type)
        
        # Форматируем сообщение
        message_text = format_bookings_message(bookings, filter_type)
        
        # Обновляем клавиатуру с подсветкой активного фильтра
        keyboard = []
        
        # Кнопки фильтров
        filters_row = []
        if filter_type == "upcoming":
            filters_row.append(InlineKeyboardButton("📅 Предстоящие ✅", callback_data="bookings_upcoming"))
        else:
            filters_row.append(InlineKeyboardButton("📅 Предстоящие", callback_data="bookings_upcoming"))
            
        if filter_type == "completed":
            filters_row.append(InlineKeyboardButton("✅ Выполненные ✅", callback_data="bookings_completed"))
        else:
            filters_row.append(InlineKeyboardButton("✅ Выполненные", callback_data="bookings_completed"))
        
        keyboard.append(filters_row)
        
        # Вторая строка фильтров
        filters_row2 = []
        if filter_type == "cancelled":
            filters_row2.append(InlineKeyboardButton("❌ Отмененные ✅", callback_data="bookings_cancelled"))
        else:
            filters_row2.append(InlineKeyboardButton("❌ Отмененные", callback_data="bookings_cancelled"))
            
        filters_row2.append(InlineKeyboardButton("🔄 Обновить", callback_data=f"bookings_{filter_type}"))
        keyboard.append(filters_row2)
        
        # Навигационные кнопки
        keyboard.append([
            InlineKeyboardButton("👤 Профиль", callback_data="profile_requests"),
            InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
        ])
        
        await query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    except Exception as e:
        logger.error(f"Ошибка при фильтрации бронирований {filter_type} для пользователя {user_id}: {e}")
        
        error_text = f"❌ **Ошибка при загрузке {filter_type} бронирований**\n\nПопробуйте позже."
        keyboard = [
            [InlineKeyboardButton("🔄 Повторить", callback_data=f"bookings_{filter_type}")],
            [InlineKeyboardButton("🔙 К бронированиям", callback_data="tickets_requests")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            error_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ==================== MONITORING HANDLERS ====================

async def handle_monitoring_direction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора направления для мониторинга"""
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
            "⏰ **Шаг 3:** Что важнее для вас?",
            reply_markup=get_time_type_keyboard(),
            parse_mode='Markdown'
        )
        
        return CHOOSE_TIME_TYPE
        
    elif data == "back_to_date":
        # Возвращаемся к выбору даты
        await query.edit_message_text(
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
        if job_queue:
            job_queue.run_repeating(
                check_routes_for_user,
                interval=300,  # 5 минут в секундах
                first=10,      # Первый запуск через 10 секунд
                name=f"monitor_{user_id}",
                data=user_id
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
    text = security.sanitize_input(update.message.text)
    
    if user_id not in user_data_store:
        # Обычный поиск рейсов
        await handle_regular_search(update, context)
        return
    
    # Проверяем, что пользователь вводит в процессе настройки
    current_state = context.user_data.get('state')
    
    # Ввод даты
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

async def check_routes_for_user(context: ContextTypes.DEFAULT_TYPE):
    """Проверка рейсов для конкретного пользователя"""
    user_id = context.job.data
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
            await send_monitoring_notification(user_id, suitable_routes, config, context)
    
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

async def send_monitoring_notification(
    user_id: int,
    routes: List,
    config: Dict,
    context: Optional[ContextTypes.DEFAULT_TYPE] = None,
):
    """Отправка уведомления о найденных рейсах"""
    try:
        bot = context.bot if context else application.bot
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
            # Убираем "| Евротранспорт-Сервис" из уведомлений
            message_parts.append(f"{emoji} **{seats} мест**")
            message_parts.append("")
        
        if len(routes) > 5:
            message_parts.append(f"... и еще {len(routes) - 5} рейсов")
        
        message_parts.extend([
            "",
            "📡 Мониторинг продолжается..."
        ])
        
        message = "\n".join(message_parts)
        
        # Создаем кнопки с веб-приложениями
        keyboard_buttons = [
            [InlineKeyboardButton("🛑 Остановить мониторинг", callback_data="stop_monitoring")],
            [InlineKeyboardButton("📊 Управление", callback_data="manage_monitoring")]
        ]
        
        # Добавляем кнопку веб-приложения для быстрого бронирования
        webapp_keyboard = create_webapp_keyboard(config['direction'], config['date'], keyboard_buttons)
        
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown',
            reply_markup=webapp_keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")

# ==================== NEW SEARCH FUNCTIONS ====================

async def handle_direction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора направления для поиска"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Сохраняем выбранное направление
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    
    user_data_store[user_id]['search_direction'] = data.replace('search_dir_', '')
    
    # Показываем календарь для выбора даты
    keyboard = get_date_keyboard()
    
    await query.edit_message_text(
        "📅 **Выберите дату для поиска рейсов:**",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    return SEARCH_DATE

async def handle_search_with_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка поиска с выбранным направлением и датой"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    date = query.data.replace('date_', '')
    
    user_data = user_data_store.get(user_id, {})
    direction = user_data.get('search_direction', 'both')
    
    await query.edit_message_text(
        f"🔍 **Ищу рейсы на {date}...**",
        parse_mode='Markdown'
    )
    
    try:
        await init_parser()
        routes_data = await parser.get_all_routes(date)
        message = format_routes_message(routes_data, date, direction)
        
        # Создаем клавиатуру с веб-приложениями в зависимости от направления
        webapp_keyboard = create_webapp_keyboard(direction, date, [
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ])
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=webapp_keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка поиска рейсов: {e}")
        await query.edit_message_text(
            "❌ **Ошибка поиска рейсов**\n\nПопробуйте позже.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Повторить поиск", callback_data="search_routes")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
    
    # Очищаем временные данные
    if user_id in user_data_store:
        user_data_store[user_id].pop('search_direction', None)
    
    return ConversationHandler.END

# ==================== COMMAND HANDLERS ====================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
    
    help_text = """❓ **Справка по использованию**

🔍 **Поиск рейсов:**
• Отправьте дату в формате YYYY-MM-DD
• Например: `2025-01-15`

🔔 **Мониторинг:**
• Выберите дату, направление и время
• Бот проверяет каждые 5 минут
• Уведомления при появлении мест

📊 **Команды:**
• `/start` - главное меню
• `/monitoring` - управление мониторингом
• `/profile` - ваш профиль
• `/booking` - автоматическое бронирование
• `/help` - эта справка

🛠 **Система диагностики (админ):**
• `/status` - статус системы мониторинга крашей
• `/recovery_history` - история восстановлений
• `/system_health` - проверка здоровья системы

🚌 **Направления:**
• Минск → Островец
• Островец → Минск"""
    
    await update.message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус системы диагностики"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if admin_panel and not admin_panel.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return
    
    try:
        status_info = {
            "crash_handler": crash_handler is not None,
            "diagnostic_system": diagnostic_system is not None,
            "auto_recovery": auto_recovery is not None,
            "railway_environment": bool(os.getenv('RAILWAY_SERVICE_NAME')),
            "github_token": bool(os.getenv('GITHUB_TOKEN')),
            "telegram_notifications": bool(os.getenv('ADMIN_TELEGRAM_ID')),
            "crash_logs_count": len(list(Path('crash_logs').glob('*.json'))) if Path('crash_logs').exists() else 0,
            "recovery_attempts": len(auto_recovery.recovery_log) if auto_recovery else 0
        }
        
        status_text = f"""🛡️ **СТАТУС СИСТЕМЫ ДИАГНОСТИКИ**

🔧 **Компоненты:**
• Crash Handler: {'✅ Активен' if status_info['crash_handler'] else '❌ Неактивен'}
• Диагностическая система: {'✅ Активна' if status_info['diagnostic_system'] else '❌ Неактивна'}
• Автовосстановление: {'✅ Активно' if status_info['auto_recovery'] else '❌ Неактивно'}

🌐 **Окружение:**
• Railway: {'✅ Да' if status_info['railway_environment'] else '❌ Нет'}
• GitHub токен: {'✅ Настроен' if status_info['github_token'] else '❌ Отсутствует'}
• Telegram уведомления: {'✅ Настроены' if status_info['telegram_notifications'] else '❌ Отсутствуют'}

📊 **Статистика:**
• Логов крашей: {status_info['crash_logs_count']}
• Попыток восстановления: {status_info['recovery_attempts']}

⏰ **Последняя проверка:** {datetime.now().strftime('%H:%M:%S')}"""
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка получения статуса: {str(e)}")

async def recovery_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает историю автоматических восстановлений"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if admin_panel and not admin_panel.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return
    
    try:
        if not auto_recovery:
            await update.message.reply_text("❌ Система автовосстановления недоступна")
            return
        
        recent_recoveries = auto_recovery.get_recovery_history(days=7)
        
        if not recent_recoveries:
            await update.message.reply_text("📝 История восстановлений пуста (последние 7 дней)")
            return
        
        history_text = "🔧 **ИСТОРИЯ АВТОМАТИЧЕСКИХ ВОССТАНОВЛЕНИЙ**\n\n"
        
        for recovery in recent_recoveries[-5:]:  # Последние 5 записей
            success = recovery.get('success', False)
            timestamp = recovery.get('timestamp', '')
            crash_id = recovery.get('crash_id', 'unknown')
            actions_count = len(recovery.get('actions_taken', []))
            
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%d.%m %H:%M')
            except:
                time_str = timestamp[:16] if timestamp else 'unknown'
            
            status_emoji = "✅" if success else "❌"
            
            history_text += f"{status_emoji} **{time_str}**\n"
            history_text += f"   🆔 Crash ID: `{crash_id[:12]}...`\n"
            history_text += f"   🛠 Действий: {actions_count}\n"
            history_text += f"   📊 Результат: {'Успешно' if success else 'Неудачно'}\n\n"
        
        if len(recent_recoveries) > 5:
            history_text += f"📊 Всего записей за 7 дней: {len(recent_recoveries)}"
        
        await update.message.reply_text(history_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка получения истории: {str(e)}")

async def system_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет здоровье системы"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if admin_panel and not admin_panel.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return
    
    try:
        await update.message.reply_text("🔍 Проверяю здоровье системы...")
        
        # Собираем информацию о системе
        import psutil
        import platform
        
        # Проверка системных ресурсов
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Проверка сетевого подключения
        network_ok = True
        try:
            response = requests.get('https://api.telegram.org', timeout=10)
            network_ok = response.status_code == 200
        except:
            network_ok = False
        
        # Проверка файловой системы
        critical_files_ok = True
        critical_files = ['src/bot.py', 'requirements.txt']
        for file_path in critical_files:
            if not Path(file_path).exists():
                critical_files_ok = False
                break
        
        # Проверка логов
        log_dir = Path('logs')
        log_files_ok = log_dir.exists() and any(log_dir.glob('*.log'))
        
        # Формируем отчет
        health_text = f"""🏥 **ЗДОРОВЬЕ СИСТЕМЫ**

💻 **Системные ресурсы:**
• CPU: {cpu_percent:.1f}% {'✅' if cpu_percent < 80 else '⚠️' if cpu_percent < 95 else '❌'}
• Память: {memory.percent:.1f}% {'✅' if memory.percent < 80 else '⚠️' if memory.percent < 95 else '❌'}
• Диск: {disk.percent:.1f}% {'✅' if disk.percent < 80 else '⚠️' if disk.percent < 95 else '❌'}

🌐 **Сетевое подключение:**
• Telegram API: {'✅ Доступен' if network_ok else '❌ Недоступен'}

📁 **Файловая система:**
• Критичные файлы: {'✅ В порядке' if critical_files_ok else '❌ Проблемы'}
• Система логирования: {'✅ Работает' if log_files_ok else '❌ Проблемы'}

🖥 **Платформа:**
• Система: {platform.system()} {platform.release()}
• Python: {platform.python_version()}
• Архитектура: {platform.machine()}

⏰ **Время проверки:** {datetime.now().strftime('%H:%M:%S')}"""
        
        # Общая оценка здоровья
        health_score = sum([
            cpu_percent < 80,
            memory.percent < 80,
            disk.percent < 80,
            network_ok,
            critical_files_ok,
            log_files_ok
        ]) / 6 * 100
        
        if health_score >= 80:
            health_text += f"\n\n🎯 **Общая оценка:** {health_score:.0f}% - Отличное состояние ✅"
        elif health_score >= 60:
            health_text += f"\n\n🎯 **Общая оценка:** {health_score:.0f}% - Удовлетворительное состояние ⚠️"
        else:
            health_text += f"\n\n🎯 **Общая оценка:** {health_score:.0f}% - Требует внимания ❌"
        
        await update.message.reply_text(health_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка проверки здоровья системы: {str(e)}")

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
    """Начало процесса поиска рейсов с выбором направления"""
    # Создаем клавиатуру для выбора направления
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙️ Минск → Островец", callback_data="search_dir_minsk_ostrovets")],
        [InlineKeyboardButton("🏘️ Островец → Минск", callback_data="search_dir_ostrovets_minsk")],
        [InlineKeyboardButton("🔄 Оба направления", callback_data="search_dir_both")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    if update.message:
        await update.message.reply_text(
            "🛣️ **Выберите направление для поиска:**",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "🛣️ **Выберите направление для поиска:**",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    return SEARCH_FROM

def format_routes_message(routes_data, date, direction='both'):
    """Форматирование сообщения с рейсами"""
    if not routes_data.get('success', False):
        return "❌ **Не удалось получить данные**"
    
    minsk_routes = routes_data.get('minsk_to_ostrovets', [])[:8]
    ostrovets_routes = routes_data.get('ostrovets_to_minsk', [])[:8]
    
    # Определяем направление из данных direction
    if direction == 'search_dir_minsk_ostrovets':
        direction = 'minsk_ostrovets'
    elif direction == 'search_dir_ostrovets_minsk':
        direction = 'ostrovets_minsk'
    elif direction == 'search_dir_both':
        direction = 'both'
    
    parts = [f"📅 **Рейсы на {date}**", ""]
    
    # Показываем только выбранное направление
    if direction == 'minsk_ostrovets' and minsk_routes:
        parts.append("🚌 **Минск → Островец:**")
        for i, route in enumerate(minsk_routes, 1):
            seats = route.get('available_seats', 0)
            emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
            parts.append(f"{i}. **{route.get('departure_time')} → {route.get('arrival_time')}** ({route.get('duration', 'н/д')})")
            parts.append(f"   {emoji} {seats} мест")
        parts.append(f"\n📊 **Всего рейсов:** {len(minsk_routes)}")
        
    elif direction == 'ostrovets_minsk' and ostrovets_routes:
        parts.append("🚌 **Островец → Минск:**")
        for i, route in enumerate(ostrovets_routes, 1):
            seats = route.get('available_seats', 0)
            emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
            parts.append(f"{i}. **{route.get('departure_time')} → {route.get('arrival_time')}** ({route.get('duration', 'н/д')})")
            parts.append(f"   {emoji} {seats} мест")
        parts.append(f"\n📊 **Всего рейсов:** {len(ostrovets_routes)}")
        
    elif direction == 'both':
        # Показываем оба направления только если выбрано "оба"
        if minsk_routes:
            parts.append("🚌 **Минск → Островец:**")
            for i, route in enumerate(minsk_routes, 1):
                seats = route.get('available_seats', 0)
                emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
                parts.append(f"{i}. **{route.get('departure_time')} → {route.get('arrival_time')}** ({route.get('duration', 'н/д')})")
                parts.append(f"   {emoji} {seats} мест")
            parts.append("")
        
        if ostrovets_routes:
            parts.append("🚌 **Островец → Минск:**")
            for i, route in enumerate(ostrovets_routes, 1):
                seats = route.get('available_seats', 0)
                emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
                parts.append(f"{i}. **{route.get('departure_time')} → {route.get('arrival_time')}** ({route.get('duration', 'н/д')})")
                parts.append(f"   {emoji} {seats} мест")
        
        total = len(minsk_routes) + len(ostrovets_routes)
        parts.append(f"\n📊 **Всего рейсов:** {total}")
    else:
        parts.append("❌ **Рейсы не найдены для выбранного направления**")
    
    return "\n".join(parts)

# ==================== CALLBACK HANDLERS ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общий обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    
    # Sanitize callback data to prevent injection attacks
    data = security.sanitize_callback_data(query.data)
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
                if job_queue:
                    # Удаляем существующие задания
                    current_jobs = job_queue.get_jobs_by_name(f"monitor_{user_id}")
                    for job in current_jobs:
                        job.schedule_removal()
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
        # Новый поиск с выбором направления
        await handle_regular_search(update, context)
    
    elif data.startswith("search_dir_"):
        # Обработка выбора направления для поиска
        await handle_direction_choice(update, context)
    
    elif data.startswith("date_") and user_id in user_data_store and 'search_direction' in user_data_store[user_id]:
        # Поиск с выбранным направлением и датой
        await handle_search_with_direction(update, context)
    
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
        # Очищаем данные пользователя при возврате в главное меню
        if user_id in user_data_store:
            del user_data_store[user_id]
            
        text = (
            "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
            "🛣️ **Направления:** Минск ⇄ Островец\n"
            "🌐 **Источник:** билет.маршруточка.бел\n\n"
            "💡 **Выберите действие:**"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    elif data == "login_requests":
        # Запускаем процесс входа - это обработается ConversationHandler
        await start_login_requests(update, context)
        return LOGIN_REQUESTS_PHONE
    
    elif data == "profile_requests":
        # Вызываем обработчик профиля
        await get_profile_requests(update, context)
    
    elif data == "tickets_requests":
        # Вызываем обработчик билетов
        await get_tickets_requests(update, context)
    
    elif data == "logout_requests":
        # Вызываем обработчик выхода
        await logout_requests(update, context)
    
    elif data.startswith("bookings_"):
        # Обработчик фильтрации бронирований (bookings_upcoming, bookings_completed, bookings_cancelled)
        await handle_bookings_filter(update, context)
    
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
                [InlineKeyboardButton("📱 Проверить сейчас", callback_data="check_now")]
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
            
            # Создаем фейковый job объект для check_routes_for_user
            class FakeJob:
                def __init__(self, data):
                    self.data = data
            
            class FakeContext:
                def __init__(self, bot):
                    self.bot = bot
                    self.job = FakeJob(user_id)
            
            fake_context = FakeContext(query.bot)
            await check_routes_for_user(fake_context)
            
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
    
    elif data == "auto_booking":
        # Переход к автобронированию
        await handle_auto_booking_menu(update, context)
    
    elif data == "admin_panel":
        # Админ-панель
        await handle_admin_panel(update, context)
    
    # Обработчики админ-панели
    elif data.startswith("admin_"):
        await handle_admin_functions(update, context, data)
    
    # Обработчики автобронирования
    elif data == "my_bookings":
        await handle_my_bookings(update, context)
    
    elif data == "auto_book_monitoring":
        await query.edit_message_text(
            "🔔 **АВТОБРОНИРОВАНИЕ ПРИ МОНИТОРИНГЕ**\n\n"
            "🚧 Функция в разработке\n\n"
            "Эта функция позволит автоматически бронировать рейсы, "
            "когда они появляются в процессе мониторинга.\n\n"
            "💡 Скоро будет доступна!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Автобронирование", callback_data="auto_booking")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
    
    else:
        await query.answer("❓ Неизвестная команда")

# ==================== AUTO BOOKING FUNCTIONS ====================

async def handle_auto_booking_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню автобронирования"""
    query = update.callback_query
    user_id = query.from_user.id
    # Предпочитаем новую систему авторизации (bot_auth_manager). Если пользователь не авторизован там,
    # пробуем legacy user_sessions (RequestsAuthManager). Иначе просим авторизоваться.
    legacy_ok = user_id in user_sessions
    if not bot_auth_manager.is_authenticated(user_id) and not legacy_ok:
        await query.edit_message_text(
            "🔒 **Автобронирование недоступно**\n\n"
            "Для использования автобронирования необходимо войти в аккаунт (кнопка ниже).",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔒 Войти в аккаунт", callback_data="login_requests"),
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
            ]]),
            parse_mode='Markdown'
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("📅 Забронировать рейс", callback_data="book_route")],
        [InlineKeyboardButton("🎫 Мои бронирования", callback_data="my_bookings")],
        [InlineKeyboardButton("🔔 Автобронирование при мониторинге", callback_data="auto_book_monitoring")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        "🤖 **АВТОБРОНИРОВАНИЕ РЕЙСОВ**\n\n"
        "🎯 Доступные функции:\n"
        "• Ручное бронирование конкретного рейса\n"
        "• Просмотр существующих бронирований\n"
        "• Автоматическое бронирование при мониторинге\n\n"
        "💡 Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать существующие бронирования пользователя"""
    query = update.callback_query
    user_id = query.from_user.id
    
    use_new = bot_auth_manager.is_authenticated(user_id)
    if not use_new and user_id not in user_sessions:
        await query.answer("❌ Необходима авторизация")
        return
    
    await query.answer("📋 Загружаю ваши бронирования...")
    
    try:
        if use_new:
            # Используем новый менеджер авторизации
            bookings = bot_auth_manager.get_user_bookings(user_id, "upcoming")
            # Преобразуем формат при необходимости
            if bookings and isinstance(bookings, list) and hasattr(bookings[0], '__dict__'):
                bookings = [b.__dict__ for b in bookings]
        else:
            auth_manager = user_sessions[user_id]
            booking_manager = AutoBookingManager(auth_manager)
            # Получаем список бронирований асинхронно (legacy)
            loop = asyncio.get_event_loop()
            bookings = await loop.run_in_executor(None, booking_manager.get_user_bookings)
        
        if bookings:
            message_parts = [
                "🎫 **ВАШИ БРОНИРОВАНИЯ**",
                ""
            ]
            
            for i, booking in enumerate(bookings[:10], 1):  # Показываем первые 10
                booking_id = booking.get('booking_id', 'н/д')
                route = booking.get('route', 'неизвестно')
                date = booking.get('date', 'н/д')
                status = booking.get('status', 'unknown')
                
                status_emoji = {
                    'confirmed': '✅',
                    'active': '🟢', 
                    'cancelled': '❌',
                    'expired': '⏰',
                    'paid': '💰'
                }.get(status, '❓')
                
                message_parts.append(
                    f"**{i}. Бронирование #{booking_id}**\n"
                    f"   🛣️ {route}\n"
                    f"   📅 {date}\n"
                    f"   {status_emoji} {status}\n"
                )
            
            if len(bookings) > 10:
                message_parts.append(f"... и еще {len(bookings) - 10} бронирований")
            
            message_text = "\n".join(message_parts)
        else:
            message_text = "🎫 **ВАШИ БРОНИРОВАНИЯ**\n\n❌ У вас нет активных бронирований"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="my_bookings")],
            [InlineKeyboardButton("🤖 Автобронирование", callback_data="auto_booking")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения бронирований: {e}")
        await query.edit_message_text(
            "❌ **Ошибка получения бронирований**\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
            ]]),
            parse_mode='Markdown'
        )

# ==================== ADMIN PANEL FUNCTIONS ====================

async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главной админ-панели"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not admin_panel or not admin_panel.is_admin(user_id):
        await query.answer("❌ У вас нет прав администратора")
        return
    
    await query.edit_message_text(
        "⚙️ **АДМИНИСТРАТИВНАЯ ПАНЕЛЬ**\n\n"
        "🔧 Добро пожаловать в админ-панель!\n"
        "Здесь вы можете управлять ботом и мониторить его работу.\n\n"
        "💡 Выберите действие:",
        reply_markup=admin_panel.get_admin_menu_keyboard(),
        parse_mode='Markdown'
    )

async def handle_admin_functions(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Обработчик функций админ-панели"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not admin_panel or not admin_panel.is_admin(user_id):
        await query.answer("❌ У вас нет прав администратора")
        return
    
    if action == "admin_monitoring_stats":
        # Статистика мониторингов
        stats_text = admin_panel.get_monitoring_statistics(active_monitors, user_sessions)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_monitoring_stats")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "admin_active_users":
        # Активные пользователи
        users_text = admin_panel.get_active_users_info(active_monitors, user_sessions, user_data_store)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_active_users")],
            [InlineKeyboardButton("🔍 Поиск пользователя", callback_data="admin_search_user")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            users_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "admin_system_logs":
        # Системные логи
        logs_text = admin_panel.get_system_logs()
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_system_logs")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            logs_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "admin_bot_settings":
        # Настройки бота
        settings_text = admin_panel.get_bot_settings()
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_bot_settings")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "admin_emergency":
        # Экстренные функции
        await query.edit_message_text(
            "🚨 **ЭКСТРЕННЫЕ ФУНКЦИИ**\n\n"
            "⚠️ **ВНИМАНИЕ!** Эти функции могут повлиять на работу бота.\n"
            "Используйте их только при необходимости.\n\n"
            "💡 Выберите действие:",
            reply_markup=admin_panel.get_emergency_functions_keyboard(),
            parse_mode='Markdown'
        )
    
    elif action == "admin_stop_all_monitoring":
        # Остановка всех мониторингов
        result = admin_panel.stop_all_monitoring(active_monitors, job_queue)
        
        keyboard = [
            [InlineKeyboardButton("🔙 Экстренные функции", callback_data="admin_emergency")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            result,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "admin_clear_user_cache":
        # Очистка кэша
        result = admin_panel.clear_user_cache(user_data_store, user_sessions)
        
        keyboard = [
            [InlineKeyboardButton("🔙 Экстренные функции", callback_data="admin_emergency")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            result,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "admin_export_data":
        # Экспорт данных
        await query.answer("📤 Экспортирую данные...")
        
        export_result = admin_panel.export_data(active_monitors, user_sessions)
        
        if export_result['success']:
            message_text = (
                f"📤 **ЭКСПОРТ ДАННЫХ ЗАВЕРШЕН**\n\n"
                f"✅ Данные сохранены в файл:\n"
                f"`{export_result['filename']}`\n\n"
                f"📊 **Статистика:**\n"
                f"• Мониторингов: {len(active_monitors)}\n"
                f"• Пользователей: {export_result['data']['total_users']}\n"
                f"• Дата экспорта: {export_result['data']['timestamp'][:19].replace('T', ' ')}"
            )
        else:
            message_text = f"📤 **ОШИБКА ЭКСПОРТА**\n\n❌ {export_result['error']}"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Экстренные функции", callback_data="admin_emergency")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ==================== PROFILE AND BOOKING COMMANDS ====================

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для входа в аккаунт"""
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        await update.message.reply_text(
            "✅ **Вы уже авторизованы в системе!**\n\n"
            "👤 Используйте кнопку \"Мой профиль\" для просмотра данных\n"
            "🎫 Используйте кнопку \"Мои билеты\" для просмотра броней",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔐 **Вход в аккаунт маршруточки**\n\n"
        "📱 Введите ваш номер телефона в формате +375XXXXXXXXX:",
        parse_mode='Markdown'
    )
    
    return LOGIN_PHONE

async def handle_login_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет номер телефона и запрашивает пароль"""
    phone = security.sanitize_input(update.message.text, max_length=20)
    user_id = update.effective_user.id

    if not security.validate_phone(phone):
        security.log_security_event("invalid_legacy_phone_format", user_id, {"phone": phone})
        await update.message.reply_text(
            "❌ **Неверный формат номера**\n\n"
            "Введите номер в формате: `+375XXXXXXXXX`",
            parse_mode='Markdown'
        )
        return LOGIN_PHONE # Stay in the same state

    context.user_data['login_phone'] = phone

    await update.message.reply_text(
        "🔑 Введите пароль от аккаунта:",
        parse_mode='Markdown'
    )

    return LOGIN_PASSWORD

async def handle_login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проводит авторизацию пользователя"""
    user_id = update.effective_user.id
    password = security.sanitize_input(update.message.text)
    phone = context.user_data.get('login_phone', '')

    if not phone:
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте снова, нажав /start.")
        return ConversationHandler.END

    await update.message.reply_text(
        "⏳ **Проверяю данные...**",
        parse_mode='Markdown'
    )

    try:
        # Создаем новый экземпляр менеджера для этого пользователя
        auth_manager = RequestsAuthManager()
        
        # Выполняем вход
        success = auth_manager.login(phone, password)
        
        if success:
            # Сохраняем номер телефона для восстановления сессии
            auth_manager.phone = phone
            user_sessions[user_id] = auth_manager
            
            # Сохраняем сессии в файл
            save_user_sessions()
            
            await update.message.reply_text(
                "🎉 **Вход выполнен успешно!**\n\n"
                "Теперь вы можете:\n"
                "• 👤 Просматривать свой профиль\n"
                "• 🎫 Смотреть свои билеты\n"
                "• 🚪 Выйти из аккаунта\n\n"
                "💡 Ваша сессия сохранена и восстановится при перезапуске бота.",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **Ошибка входа.**\n\nПожалуйста, проверьте ваш телефон и пароль и попробуйте снова.",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {e}")
        await update.message.reply_text(
            "❌ **Ошибка системы. Попробуйте позже.**",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    # Очищаем временные данные
    if 'login_phone' in context.user_data:
        del context.user_data['login_phone']
    
    return ConversationHandler.END

# ==================== BOOKING CONVERSATION FUNCTIONS ====================

async def start_booking_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса бронирования рейса"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in user_sessions:
        await query.edit_message_text(
            "🔒 **Бронирование недоступно**\n\n"
            "Для бронирования рейсов необходимо войти в аккаунт.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔒 Войти в аккаунт", callback_data="login_requests"),
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
            ]]),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Очищаем предыдущие данные бронирования
    context.user_data.clear()
    context.user_data['booking_stage'] = 'passenger_count'
    
    # Клавиатура для выбора количества пассажиров
    keyboard = []
    for count in range(1, 3):  # От 1 до 2 пассажиров (максимум по правилам сайта)
        keyboard.append([InlineKeyboardButton(
            f"{count} {'пассажир' if count == 1 else 'пассажира'}",
            callback_data=f"passengers_{count}"
        )])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_booking")])
    
    await query.edit_message_text(
        "🎫 **БРОНИРОВАНИЕ РЕЙСА**\n\n"
        "👥 Выберите количество пассажиров:\n\n"
        "💡 Максимальное количество пассажиров: 2",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return CHOOSE_PASSENGER_COUNT

async def handle_passenger_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора количества пассажиров"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if query.data == "cancel_booking":
        await query.edit_message_text(
            "❌ Бронирование отменено",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
            ]])
        )
        return ConversationHandler.END
    
    if query.data.startswith("passengers_"):
        passenger_count = int(query.data.split("_")[1])
        context.user_data['passenger_count'] = passenger_count
        
        await query.answer(f"✅ Выбрано {passenger_count} пассажиров")
        
        try:
            # Получаем доступные маршруты
            auth_manager = user_sessions[user_id]
            booking_manager = AutoBookingManager(auth_manager)
            
            await query.edit_message_text(
                "🔄 Загружаю доступные маршруты...",
                parse_mode='Markdown'
            )
            
            # Получаем маршруты асинхронно
            loop = asyncio.get_event_loop()
            routes = await loop.run_in_executor(None, booking_manager.get_available_routes)
            
            if routes:
                keyboard = []
                for route in routes[:10]:  # Показываем первые 10 маршрутов
                    route_id = route.get('route_id', '')
                    route_name = route.get('name', 'Неизвестный маршрут')
                    date = route.get('date', '')
                    time = route.get('time', '')
                    available = route.get('available_seats', 0)
                    
                    button_text = f"{route_name}"
                    if date:
                        button_text += f" ({date}"
                    if time:
                        button_text += f", {time}"
                    if available > 0:
                        button_text += f", свободно: {available}"
                    if date:
                        button_text += ")"
                    
                    keyboard.append([InlineKeyboardButton(
                        button_text[:64],  # Ограничиваем длину
                        callback_data=f"route_{route_id}"
                    )])
                
                keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_booking")])
                
                await query.edit_message_text(
                    f"🛣️ **ДОСТУПНЫЕ МАРШРУТЫ**\n\n"
                    f"👥 Пассажиров: {passenger_count}\n"
                    f"📋 Найдено маршрутов: {len(routes)}\n\n"
                    f"💡 Выберите маршрут для бронирования:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
                return CONFIRM_BOOKING
            else:
                await query.edit_message_text(
                    "❌ **Нет доступных маршрутов**\n\n"
                    "В данный момент нет доступных маршрутов для бронирования.\n"
                    "Попробуйте позже.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                    ]]),
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Ошибка загрузки маршрутов: {e}")
            await query.edit_message_text(
                "❌ **Ошибка загрузки маршрутов**\n\n"
                "Попробуйте позже или обратитесь к администратору.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                ]]),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    
    return CHOOSE_PASSENGER_COUNT

async def handle_route_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения бронирования маршрута"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if query.data == "cancel_booking":
        await query.edit_message_text(
            "❌ Бронирование отменено",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
            ]])
        )
        return ConversationHandler.END
    
    if query.data.startswith("route_"):
        route_id = query.data.replace("route_", "")
        passenger_count = context.user_data.get('passenger_count', 1)
        
        await query.answer("🎫 Бронирую маршрут...")
        
        await query.edit_message_text(
            "🔄 **ПРОЦЕСС БРОНИРОВАНИЯ**\n\n"
            "Пожалуйста, подождите...\n"
            "Выполняю бронирование маршрута.",
            parse_mode='Markdown'
        )
        
        try:
            auth_manager = user_sessions[user_id]
            booking_manager = AutoBookingManager(auth_manager)
            
            # Выполняем бронирование асинхронно
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                booking_manager.auto_book_route, 
                route_id, 
                passenger_count
            )
            
            if result['success']:
                message_text = (
                    "✅ **БРОНИРОВАНИЕ УСПЕШНО!**\n\n"
                    f"🎫 ID бронирования: `{result.get('booking_id', 'н/д')}`\n"
                    f"🛣️ Маршрут: {result.get('route_name', 'н/д')}\n"
                    f"📅 Дата: {result.get('date', 'н/д')}\n"
                    f"⏰ Время: {result.get('time', 'н/д')}\n"
                    f"👥 Пассажиров: {passenger_count}\n\n"
                    f"💡 Детали бронирования сохранены в вашем аккаунте.\n"
                    f"Проверить статус можно в разделе \"Мои бронирования\"."
                )
                
                keyboard = [
                    [InlineKeyboardButton("🎫 Мои бронирования", callback_data="my_bookings")],
                    [InlineKeyboardButton("🤖 Автобронирование", callback_data="auto_booking")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
                ]
                
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')
                message_text = (
                    "❌ **ОШИБКА БРОНИРОВАНИЯ**\n\n"
                    f"Не удалось забронировать маршрут.\n\n"
                    f"**Причина:** {error_msg}\n\n"
                    "💡 Попробуйте выбрать другой маршрут или повторите попытку позже."
                )
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data="book_route")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
                ]
            
            await query.edit_message_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Критическая ошибка бронирования: {e}")
            await query.edit_message_text(
                "❌ **КРИТИЧЕСКАЯ ОШИБКА**\n\n"
                "Произошла непредвиденная ошибка при бронировании.\n"
                "Попробуйте позже или обратитесь к администратору.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                ]]),
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
    
    return CONFIRM_BOOKING

# ==================== MAIN APPLICATION ====================

def register_handlers(application):
    """Регистрация всех обработчиков"""
    # Настройка ConversationHandler для мониторинга
    monitoring_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_monitoring_conversation, pattern="^setup_monitoring$"),
        ],
        states={
            CHOOSE_DATE: [
                CallbackQueryHandler(handle_date_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input)
            ],
            CHOOSE_DIRECTION: [
                CallbackQueryHandler(handle_monitoring_direction_choice),
            ],
            CHOOSE_TIME_TYPE: [
                CallbackQueryHandler(handle_time_type_choice),
            ],
            CHOOSE_TIME_RANGE: [
                CallbackQueryHandler(handle_time_range_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input)
            ],
            CONFIRM_MONITORING: [
                CallbackQueryHandler(handle_monitoring_confirmation),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handle_main_menu, pattern="^back_to_main$"),
            CommandHandler('start', start),
        ],
        per_message=False,
    )

    # Настройка ConversationHandler для входа через Requests
    login_requests_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_login_requests, pattern="^login_requests$"),
        ],
        states={
            LOGIN_REQUESTS_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_requests)
            ],
            LOGIN_REQUESTS_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password_requests)
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
        ],
        per_message=False,
    )

    # Настройка ConversationHandler для бронирования
    booking_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_booking_conversation, pattern="^book_route$"),
        ],
        states={
            CHOOSE_PASSENGER_COUNT: [
                CallbackQueryHandler(handle_passenger_count)
            ],
            CONFIRM_BOOKING: [
                CallbackQueryHandler(handle_route_booking)
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^cancel_booking$"),
        ],
        per_message=False,
    )

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("monitoring", monitoring_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("recovery_history", recovery_history_command))
    application.add_handler(CommandHandler("system_health", system_health_command))
    
    # Добавляем ConversationHandlers
    application.add_handler(monitoring_conv_handler)
    application.add_handler(login_requests_conv_handler)
    application.add_handler(booking_conv_handler)
    
    # Добавляем обработчики кнопок (порядок важен!)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)

def main():
    """Главная функция запуска бота"""
    global application, admin_panel
    
    # Загружаем существующие мониторинги
    try:
        load_active_monitors()
        if is_railway_logger:
            logger.system_action("Мониторинги загружены", {"count": len(active_monitors)})
        else:
            logger.info(f"📊 Загружены мониторинги для {len(active_monitors)} пользователей")
    except Exception as e:
        if is_railway_logger:
            logger.system_action("Ошибка загрузки мониторингов", {"error": str(e)}, level="error")
        else:
            logger.error(f"❌ Ошибка загрузки мониторингов: {e}")
    
    # Инициализируем систему обработки крашей в самом начале
    try:
        crash_handler.setup_crash_handling()
        if is_railway_logger:
            logger.system_action("Система обработки крашей активирована", {"status": "enabled"})
        else:
            logger.info("🛡️ Система обработки крашей активирована")
    except Exception as e:
        if is_railway_logger:
            logger.system_action("Ошибка активации crash handler", {"error": str(e)}, level="error")
        else:
            logger.error(f"❌ Ошибка активации crash handler: {e}")
    
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        if is_railway_logger:
            logger.bot_action("Токен бота не найден", {"error": "TELEGRAM_BOT_TOKEN missing"}, level="error")
        else:
            logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    # Инициализируем админ-панель
    admin_telegram_id = os.getenv('ADMIN_TELEGRAM_ID')
    if admin_telegram_id:
        try:
            admin_panel = AdminPanel(int(admin_telegram_id))
            if is_railway_logger:
                logger.admin_action("Админ-панель активирована", {"admin_id": admin_telegram_id})
            else:
                logger.info(f"👤 Админ-панель активирована для пользователя {admin_telegram_id}")
        except ValueError:
            if is_railway_logger:
                logger.admin_action("Неверный ADMIN_TELEGRAM_ID", {"error": "must_be_number"}, level="error")
            else:
                logger.error("❌ ADMIN_TELEGRAM_ID должен быть числом!")
    else:
        if is_railway_logger:
            logger.admin_action("ADMIN_TELEGRAM_ID не установлен", {"warning": "admin_panel_disabled"}, level="warning")
        else:
            logger.warning("⚠️ ADMIN_TELEGRAM_ID не установлен - админ-панель недоступна")
    
    if is_railway_logger:
        logger.bot_action("Запуск бота MarhrutochkaTG", {
            "python_version": sys.version.split()[0],
            "working_directory": os.getcwd(),
            "process_id": os.getpid(),
            "environment": "railway" if os.getenv('RAILWAY_SERVICE_NAME') else "local"
        })
    else:
        logger.info("🚀 Запуск бота MarhrutochkaTG...")
        logger.info(f"Версия Python: {sys.version}")
        logger.info(f"Рабочая директория: {os.getcwd()}")
        logger.info(f"ID процесса: {os.getpid()}")
    
    # Создаем приложение
    application = Application.builder().token(token).build()
    
    try:
        # Регистрируем обработчики
        register_handlers(application)
        
        # Получаем job_queue
        global job_queue
        job_queue = application.job_queue
        
        # Загружаем существующие мониторинги и сессии
        load_active_monitors()
        load_user_sessions()
        
        if is_railway_logger:
            logger.bot_action("Данные восстановлены", {
                "monitors_count": len(active_monitors),
                "sessions_count": len(user_sessions)
            })
        else:
            logger.info(f"📊 Загружены мониторинги для {len(active_monitors)} пользователей")
            logger.info(f"🔓 Загружены сессии для {len(user_sessions)} пользователей")
        
        # Восстанавливаем активные мониторинги
        for user_id, config in active_monitors.items():
            try:
                job_queue.run_repeating(
                    check_routes_for_user,
                    interval=300,  # 5 минут в секундах
                    first=10,      # Первый запуск через 10 секунд
                    name=f"monitor_{user_id}",
                    data=user_id
                )
                if is_railway_logger:
                    logger.bot_action(f"Мониторинг восстановлен", {"user_id": user_id})
                else:
                    logger.info(f"🔄 Восстановлен мониторинг для пользователя {user_id}")
            except Exception as e:
                if is_railway_logger:
                    logger.bot_action(f"Ошибка восстановления мониторинга", {
                        "user_id": user_id,
                        "error": str(e)
                    }, level="error")
                else:
                    logger.error(f"❌ Ошибка восстановления мониторинга для {user_id}: {e}")
        
        # Запускаем бота (планировщик запустится автоматически)
        if is_railway_logger:
            logger.bot_action("Бот запущен успешно", {"status": "running"})
        else:
            logger.info("🤖 Бот запущен успешно!")
        application.run_polling(drop_pending_updates=True)
        
    except Conflict:
        if is_railway_logger:
            logger.bot_action("Конфликт: бот уже запущен", {"error": "conflict"}, level="error")
        else:
            logger.error("❌ Конфликт: бот уже запущен в другом месте!")
    except Exception as e:
        if is_railway_logger:
            logger.bot_action("Критическая ошибка", {"error": str(e)}, level="error")
        else:
            logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        
        # Обрабатываем краш через нашу систему
        try:
            async def handle_crash():
                crash_analysis = await diagnostic_system.analyze_crash_report_from_exception(e)
                if crash_analysis:
                    recovery_result = await auto_recovery.attempt_auto_recovery(crash_analysis)
                    if is_railway_logger:
                        logger.system_action("Автоматическое восстановление завершено", {
                            "success": recovery_result.get("success", False),
                            "actions_count": len(recovery_result.get("actions_taken", [])),
                            "crash_id": crash_analysis.get("crash_id")
                        })
                    else:
                        logger.info(f"🔧 Автоматическое восстановление: {'успешно' if recovery_result.get('success') else 'неуспешно'}")
            
            # Запускаем асинхронную обработку краша
            asyncio.run(handle_crash())
            
        except Exception as recovery_error:
            if is_railway_logger:
                logger.system_action("Ошибка автоматического восстановления", {"error": str(recovery_error)}, level="error")
            else:
                logger.error(f"❌ Ошибка автоматического восстановления: {recovery_error}")
        
        traceback.print_exc()
    finally:
        # Graceful shutdown
        try:
            if job_queue:
                for job in job_queue.jobs():
                    job.schedule_removal()
                logger.info("⏰ JobQueue остановлен")
        except Exception as e:
            logger.error(f"Ошибка при завершении JobQueue: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        logger.info("🚀 Старт главной функции main()")
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Фатальная ошибка: {e}", exc_info=True)
        sys.exit(1)