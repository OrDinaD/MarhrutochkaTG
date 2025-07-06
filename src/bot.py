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
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

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

# Импортируем новый менеджер аутентификации
try:
    from .requests_auth import RequestsAuthManager
except ImportError:
    from requests_auth import RequestsAuthManager

# Импортируем парсер
try:
    from .parser import FinalMarshrutochkaParser
except ImportError:
    from parser import FinalMarshrutochkaParser

# Импортируем наш менеджер логирования
try:
    from .log_manager import setup_logging
except ImportError:
    from log_manager import setup_logging

# Настройка логирования
logger = setup_logging(logging.INFO)

# Игнорируем предупреждения от python-telegram-bot о per_message
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=PTBUserWarning)

# Отключаем подробные сообщения от httpx, используемого библиотекой telegram
logging.getLogger("httpx").setLevel(logging.WARNING)

# Состояния для ConversationHandler
(CHOOSE_DATE, CHOOSE_DIRECTION, CHOOSE_TIME_TYPE, CHOOSE_TIME_RANGE, 
 CONFIRM_MONITORING, MONITORING_ACTIVE, LOGIN_PHONE, LOGIN_PASSWORD,
 SEARCH_FROM, SEARCH_TO, SEARCH_DATE, BOOKING_NUMBER, PHONE_DIGITS,
 LOGIN_REQUESTS_PHONE, LOGIN_REQUESTS_PASSWORD) = range(15)

# Глобальные переменные
parser = None
requests_auth_manager = None # Для нового менеджера
job_queue = None  # Встроенная очередь заданий PTB
active_monitors = {}  # user_id -> monitor_config
user_data_store = {}  # user_id -> user_data
user_sessions = {} # user_id -> RequestsAuthManager instance
application = None  # will hold the Application instance
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'monitors.json')
SESSIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_sessions.json')

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

def load_user_sessions():
    """Загрузка пользовательских сессий из файла"""
    global user_sessions
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Восстанавливаем сессии RequestsAuthManager
            for user_id_str, session_data in data.items():
                user_id = int(user_id_str)
                auth_manager = RequestsAuthManager()
                
                # Восстанавливаем cookies и состояние
                if 'cookies' in session_data:
                    auth_manager.session.cookies.update(session_data['cookies'])
                if 'phone' in session_data:
                    auth_manager.phone = session_data['phone']
                if 'authenticated' in session_data and session_data['authenticated']:
                    auth_manager.authenticated = True
                    user_sessions[user_id] = auth_manager
                    logger.info(f"🔓 Восстановлена сессия для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Не удалось загрузить сессии: {e}")

def save_user_sessions():
    """Сохранение пользовательских сессий в файл"""
    try:
        data = {}
        for user_id, auth_manager in user_sessions.items():
            if hasattr(auth_manager, 'authenticated') and auth_manager.authenticated:
                session_data = {
                    'cookies': dict(auth_manager.session.cookies),
                    'phone': getattr(auth_manager, 'phone', ''),
                    'authenticated': True
                }
                data[str(user_id)] = session_data
        
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Не удалось сохранить сессии: {e}")

# Загружаем существующие мониторинги и сессии при импорте модуля
load_active_monitors()
try:
    load_user_sessions()
except Exception as e:
    logger.error(f"Ошибка при загрузке сессий: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors from telegram.ext and log them."""
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

    if user_id in user_sessions:
        # Пользователь вошел через Requests
        keyboard.extend([
            [InlineKeyboardButton("👤 Мой профиль", callback_data="profile_requests")],
            [InlineKeyboardButton("🎫 Мои билеты", callback_data="tickets_requests")],
            [InlineKeyboardButton("🚪 Выйти из аккаунта", callback_data="logout_requests")]
        ])
    else:
        # Пользователь не вошел
        keyboard.append([InlineKeyboardButton("🔒 Войти в аккаунт", callback_data="login_requests")])

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
    """Начало процесса входа через Requests"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="Пожалуйста, введите ваш номер телефона (например, +375291234567):",
        parse_mode='Markdown'
    )
    return LOGIN_REQUESTS_PHONE

async def handle_phone_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода телефона для входа через Requests"""
    phone = update.message.text
    user_id = update.effective_user.id
    context.user_data['phone'] = phone
    
    await update.message.reply_text("Теперь введите ваш пароль:")
    return LOGIN_REQUESTS_PASSWORD

async def handle_password_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пароля и попытка входа через Requests"""
    password = update.message.text
    user_id = update.effective_user.id
    phone = context.user_data.get('phone')

    if not phone:
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте снова, нажав /start.")
        return ConversationHandler.END

    await update.message.reply_text("⏳ Выполняю вход... Это может занять несколько секунд.")

    # Создаем новый экземпляр менеджера для этого пользователя
    auth_manager = RequestsAuthManager()
    
    # Выполняем вход асинхронно, чтобы не блокировать основной поток
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, lambda: auth_manager.login(phone, password))

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
    
    # Очищаем временные данные
    del context.user_data['phone']
    
    return ConversationHandler.END

async def get_profile_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение профиля пользователя через Requests"""
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        if update.callback_query:
            await update.callback_query.answer("Сначала нужно войти!", show_alert=True)
        return

    if update.callback_query:
        await update.callback_query.answer("Получаю данные профиля...")
    auth_manager = user_sessions[user_id]
    
    try:
        # Получаем данные профиля асинхронно
        loop = asyncio.get_event_loop()
        profile_data = await loop.run_in_executor(None, auth_manager.get_profile)
        
        if profile_data:
            profile_text = "**👤 Ваш профиль:**\n\n"
            for key, value in profile_data.items():
                profile_text += f"**{key.replace('_', ' ').capitalize()}:** {value}\n"
            
            profile_text += "\n💡 Используйте кнопки ниже для навигации."
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    profile_text,
                    reply_markup=get_main_menu_keyboard(user_id),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    profile_text,
                    reply_markup=get_main_menu_keyboard(user_id),
                    parse_mode='Markdown'
                )
        else:
            error_text = "❌ **Не удалось получить данные профиля.**\n\nВозможно, сессия истекла. Попробуйте войти заново."
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    error_text,
                    reply_markup=get_main_menu_keyboard(user_id),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    error_text,
                    reply_markup=get_main_menu_keyboard(user_id),
                    parse_mode='Markdown'
                )
    except Exception as e:
        logger.error(f"Ошибка при получении профиля: {e}")
        error_text = "❌ **Произошла ошибка при получении профиля.**\n\nПопробуйте позже."
        if update.callback_query:
            await update.callback_query.edit_message_text(
                error_text,
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                error_text,
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )

async def get_tickets_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение билетов пользователя через Requests"""
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        if update.callback_query:
            await update.callback_query.answer("Сначала нужно войти!", show_alert=True)
        return

    if update.callback_query:
        await update.callback_query.answer("Получаю список ваших билетов...")
    auth_manager = user_sessions[user_id]
    
    try:
        # Получаем билеты асинхронно
        loop = asyncio.get_event_loop()
        tickets = await loop.run_in_executor(None, auth_manager.get_tickets)
        
        if tickets:
            message_text = "**🎫 Ваши активные билеты:**\n\n"
            for i, ticket in enumerate(tickets, 1):
                message_text += f"**Билет #{i}:**\n"
                for key, value in ticket.items():
                    message_text += f"• **{key.replace('_', ' ').capitalize()}:** {value}\n"
                message_text += "\n"
        else:
            message_text = "📭 **У вас нет активных билетов.**\n\n💡 Вы можете забронировать билеты на сайте билет.маршруточка.бел"

        message_text += "\n💡 Используйте кнопки ниже для навигации."

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Ошибка при получении билетов: {e}")
        error_text = "❌ **Произошла ошибка при получении билетов.**\n\nПопробуйте позже."
        if update.callback_query:
            await update.callback_query.edit_message_text(
                error_text,
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                error_text,
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )

async def logout_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из аккаунта"""
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        # Удаляем сессию пользователя
        del user_sessions[user_id]
        
        # Сохраняем изменения в файл
        save_user_sessions()
        
        await update.callback_query.answer("Выход выполнен")
        await update.callback_query.edit_message_text(
            "🚪 **Выход выполнен успешно!**\n\n"
            "💡 Чтобы снова войти в аккаунт, используйте кнопку \"🔒 Войти в аккаунт\"",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.answer("Вы не были авторизованы", show_alert=True)


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
    text = update.message.text.strip()
    
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

# ==================== COMMAND HANDLERS ====================

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

async def handle_login_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет номер телефона и запрашивает пароль"""
    phone = update.message.text.strip()
    context.user_data['login_phone'] = phone

    await update.message.reply_text(
        "🔑 Введите пароль от аккаунта:",
        parse_mode='Markdown'
    )

    return LOGIN_PASSWORD

async def handle_login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проводит авторизацию пользователя"""
    user_id = update.effective_user.id
    password = update.message.text.strip()
    phone = context.user_data.get('login_phone', '')

    await update.message.reply_text(
        "⏳ **Проверяю данные...**",
        parse_mode='Markdown'
    )

    try:
        await init_auth_manager()
        success = await auth_manager.login(phone, password)
        if success:
            user_auth[user_id] = {'authenticated': True}
            await update.message.reply_text(
                "✅ **Успешный вход!**",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **Не удалось войти. Проверьте данные и попробуйте снова.**",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {e}")
        await update.message.reply_text(
            "❌ **Ошибка системы. Попробуйте позже.**",
            parse_mode='Markdown'
        )
    
    return ConversationHandler.END

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
                CallbackQueryHandler(handle_direction_choice),
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

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("monitoring", monitoring_command))
    
    # Добавляем ConversationHandlers
    application.add_handler(monitoring_conv_handler)
    application.add_handler(login_requests_conv_handler)
    
    # Добавляем обработчики кнопок (порядок важен!)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)

def main():
    """Главная функция запуска бота"""
    global application
    
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    logger.info("🚀 Запуск бота MarhrutochkaTG...")
    
    # Логируем информацию о версии и окружении
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
                logger.info(f"🔄 Восстановлен мониторинг для пользователя {user_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка восстановления мониторинга для {user_id}: {e}")
        
        # Запускаем бота (планировщик запустится автоматически)
        logger.info("🤖 Бот запущен успешно!")
        application.run_polling(drop_pending_updates=True)
        
    except Conflict:
        logger.error("❌ Конфликт: бот уже запущен в другом месте!")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
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