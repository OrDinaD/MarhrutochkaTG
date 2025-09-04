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
    from .auth import (RequestsAuthManager, bot_auth_manager, format_profile_message, 
                      format_bookings_message, format_routes_message, format_booking_confirmation,
                      RouteInfo, BookingRequest)
    from .utils import FinalMarshrutochkaParser, AutoBookingManager
    from .monitoring import setup_logging, railway_logger, crash_handler, diagnostic_system, auto_recovery
    from .admin_panel import AdminPanel
    from .security import security
    from .database import db_manager
except ImportError:
    from auth import (RequestsAuthManager, bot_auth_manager, format_profile_message, 
                     format_bookings_message, format_routes_message, format_booking_confirmation,
                     RouteInfo, BookingRequest)
    from utils import FinalMarshrutochkaParser, AutoBookingManager
    from monitoring import setup_logging, railway_logger, crash_handler, diagnostic_system, auto_recovery
    from admin_panel import AdminPanel
    from security import security
    from database import db_manager

# Настройка логирования - используем Railway enhanced logger если доступен
if railway_logger:
    logger = railway_logger
else:
    logger = setup_logging(logging.INFO)

# Определяем, является ли logger Railway logger-ом по наличию специальных методов
is_railway_logger = hasattr(logger, 'system_action') and hasattr(logger, 'bot_action')

def safe_log_system(message: str, data: dict = None, level: str = "info"):
    """Безопасное логирование системных действий"""
    if hasattr(logger, 'system_action'):
        logger.system_action(message, data or {}, level=level)
    else:
        getattr(logger, level, logger.info)(f"⚙️ {message}")

def safe_log_bot(message: str, data: dict = None, level: str = "info"):
    """Безопасное логирование действий бота"""
    if hasattr(logger, 'bot_action'):
        logger.bot_action(message, data or {}, level=level)
    else:
        getattr(logger, level, logger.info)(f"🤖 {message}")

def safe_log_admin(message: str, data: dict = None, level: str = "info"):
    """Безопасное логирование действий админа"""
    if hasattr(logger, 'admin_action'):
        logger.admin_action(message, data or {}, level=level)
    else:
        getattr(logger, level, logger.info)(f"👨‍💻 {message}")

# Глобальный мониторинг состояний callback queries
active_callbacks = {}  # {user_id: {'query_id': str, 'start_time': datetime, 'handler': str}}
callback_timeout_seconds = 45  # Таймаут для застрявших callbacks

async def track_callback_start(user_id: int, query_id: str, handler_name: str):
    """Отслеживание начала callback обработки"""
    active_callbacks[user_id] = {
        'query_id': query_id,
        'start_time': datetime.now(),
        'handler': handler_name
    }
    logger.info(f"🔄 [{user_id}] Начало callback: {handler_name} (ID: {query_id})")

async def track_callback_end(user_id: int):
    """Отслеживание окончания callback обработки"""
    if user_id in active_callbacks:
        callback_info = active_callbacks.pop(user_id)
        duration = (datetime.now() - callback_info['start_time']).total_seconds()
        logger.info(f"✅ [{user_id}] Завершен callback: {callback_info['handler']} ({duration:.2f}s)")

async def cleanup_stuck_callbacks():
    """Очистка застрявших callback handlers"""
    current_time = datetime.now()
    stuck_users = []
    
    for user_id, callback_info in active_callbacks.items():
        duration = (current_time - callback_info['start_time']).total_seconds()
        if duration > callback_timeout_seconds:
            stuck_users.append(user_id)
            logger.warning(f"⚠️ [{user_id}] Застрявший callback: {callback_info['handler']} ({duration:.2f}s)")
    
    for user_id in stuck_users:
        active_callbacks.pop(user_id, None)
        logger.info(f"🧹 [{user_id}] Принудительная очистка застрявшего callback")

async def emergency_conversation_reset(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Экстренный сброс состояния разговора для пользователя"""
    try:
        # Очищаем все состояния пользователя
        context.user_data.clear()
        
        # Очищаем из глобального хранилища
        if user_id in user_data_store:
            del user_data_store[user_id]
        
        # Очищаем callback tracking
        active_callbacks.pop(user_id, None)
        
        logger.warning(f"🚨 [{user_id}] Экстренный сброс состояния conversation")
        
    except Exception as e:
        logger.error(f"❌ [{user_id}] Ошибка при экстренном сбросе: {e}")

def safe_log_admin(message: str, data: dict = None, level: str = "info"):
    """Безопасное логирование действий админа"""
    if hasattr(logger, 'admin_action'):
        logger.admin_action(message, data or {}, level=level)
    else:
        getattr(logger, level, logger.info)(f"👤 {message}")

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
 CONFIRM_BOOKING, ADMIN_SEARCH_USER, BOOKING_FROM, BOOKING_TO, BOOKING_DATE,
 BOOKING_ROUTE_SELECT, BOOKING_PASSENGER_COUNT, BOOKING_PASSENGER_NAME,
 BOOKING_PASSENGER_PHONE, BOOKING_CONFIRM) = range(26)

from telegram.error import BadRequest

# Глобальные переменные
parser = None
requests_auth_manager = None # Для нового менеджера
job_queue = None  # Встроенная очередь заданий PTB
active_monitors = {}  # user_id -> monitor_config
user_data_store = {}  # user_id -> user_data
application = None  # will hold the Application instance
admin_panel = None  # Административная панель

# Вспомогательная функция для безопасного редактирования сообщений
async def safe_edit_message(query_or_update, text: str, reply_markup=None, parse_mode=None, timeout=10):
    """Безопасное редактирование сообщения с обработкой ошибок и таймаутом"""
    import asyncio
    
    try:
        # Добавляем таймаут для предотвращения зависания
        async def _edit_message():
            if hasattr(query_or_update, 'edit_message_text'):
                # Это callback_query
                await query_or_update.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            elif hasattr(query_or_update, 'callback_query'):
                # Это update с callback_query
                await query_or_update.callback_safe_edit_message(
                query,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        
        # Выполняем с таймаутом
        await asyncio.wait_for(_edit_message(), timeout=timeout)
        
    except asyncio.TimeoutError:
        logger.error(f"⏰ Таймаут при редактировании сообщения ({timeout}s)")
        # Пытаемся отправить простое сообщение вместо редактирования
        try:
            if hasattr(query_or_update, 'message'):
                await query_or_update.message.reply_text("⚠️ Загрузка...")
        except:
            pass
            
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.debug(f"Сообщение не изменилось для пользователя, пропускаем редактирование")
            return
        elif "Message to edit not found" in str(e):
            logger.warning(f"Сообщение для редактирования не найдено")
            return
        else:
            logger.error(f"Ошибка BadRequest при редактировании сообщения: {e}")
            # Не перебрасываем ошибку, чтобы не блокировать бота
            
    except Exception as e:
        logger.error(f"Неожиданная ошибка при редактировании сообщения: {e}")
        # Не перебрасываем ошибку, чтобы не блокировать бота

async def safe_answer_callback(query, text="", timeout=5):
    """Безопасный ответ на callback query с таймаутом"""
    import asyncio
    
    try:
        # Проверяем, был ли callback уже отвечен
        if hasattr(query, '_answered') and query._answered:
            logger.debug(f"Callback {query.id} уже был отвечен")
            return
            
        await asyncio.wait_for(query.answer(text), timeout=timeout)
        # Помечаем как отвеченный
        query._answered = True
        
    except asyncio.TimeoutError:
        logger.error(f"⏰ Таймаут при ответе на callback ({timeout}s)")
    except Exception as e:
        # Игнорируем ошибки о том, что callback уже был отвечен
        if "query is too old" in str(e).lower() or "invalid query id" in str(e).lower():
            logger.debug(f"Callback query уже недействителен: {e}")
        else:
            logger.error(f"Ошибка при ответе на callback: {e}")

async def safe_send_message(update_or_context, text: str, reply_markup=None, parse_mode=None, timeout=10):
    """Безопасная отправка сообщения с таймаутом"""
    import asyncio
    
    try:
        async def _send_message():
            if hasattr(update_or_context, 'message'):
                await update_or_context.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            elif hasattr(update_or_context, 'send_message'):
                await update_or_context.send_message(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                
        await asyncio.wait_for(_send_message(), timeout=timeout)
        
    except asyncio.TimeoutError:
        logger.error(f"⏰ Таймаут при отправке сообщения ({timeout}s)")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")

def callback_handler_protection(timeout=30):
    """Улучшенный декоратор для защиты callback handlers от зависания"""
    def decorator(func):
        import asyncio
        import functools
        
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            user_id = update.effective_user.id
            handler_name = func.__name__
            
            try:
                # Проверяем на застрявшие callbacks для этого пользователя
                if user_id in active_callbacks:
                    old_callback = active_callbacks[user_id]
                    duration = (datetime.now() - old_callback['start_time']).total_seconds()
                    if duration > 10:  # Если предыдущий callback висит больше 10 секунд
                        logger.warning(f"⚠️ [{user_id}] Прерываем застрявший callback: {old_callback['handler']}")
                        await emergency_conversation_reset(user_id, context)
                
                # Отслеживаем начало нового callback
                await track_callback_start(user_id, query.id, handler_name)
                
                # Сразу отвечаем на callback чтобы убрать "загрузка"
                await safe_answer_callback(query, "")
                
                # Выполняем основную функцию с таймаутом
                result = await asyncio.wait_for(func(update, context), timeout=timeout)
                
                # Отслеживаем успешное завершение
                await track_callback_end(user_id)
                logger.info(f"✅ [{user_id}] Callback обработан успешно: {handler_name}")
                return result
                
            except asyncio.TimeoutError:
                await track_callback_end(user_id)
                logger.error(f"⏰ [{user_id}] Таймаут callback handler ({timeout}s): {handler_name}")
                
                # Экстренный сброс состояния
                await emergency_conversation_reset(user_id, context)
                
                # Пытаемся вернуть пользователя в главное меню
                try:
                    await safe_edit_message(
                        query,
                        "⚠️ **Превышено время ожидания**\n\nПроизведен сброс состояния. Возвращаемся в главное меню...",
                        reply_markup=get_main_menu_keyboard(user_id),
                        parse_mode='Markdown'
                    )
                except:
                    pass
                    
                return ConversationHandler.END
                
            except Exception as e:
                await track_callback_end(user_id)
                logger.error(f"❌ [{user_id}] Ошибка в callback handler {handler_name}: {e}", exc_info=True)
                
                # Экстренный сброс состояния при ошибке
                await emergency_conversation_reset(user_id, context)
                
                # Пытаемся вернуть пользователя в главное меню
                try:
                    await safe_edit_message(
                        query,
                        "❌ **Произошла ошибка**\n\nПроизведен сброс состояния. Возвращаемся в главное меню...",
                        reply_markup=get_main_menu_keyboard(user_id),
                        parse_mode='Markdown'
                    )
                except:
                    pass
                    
                return ConversationHandler.END
                
        return wrapper
    return decorator

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
    """Загрузка активных мониторингов из базы данных и файла (миграция)"""
    global active_monitors
    try:
        # Загружаем из базы данных
        active_monitors = {}
        
        # Получаем все активные мониторинги из БД
        # Здесь можно добавить загрузку если нужно, но лучше грузить динамически
        logger.info("Мониторинги будут загружаться из БД динамически")
        
        # Для совместимости также пытаемся загрузить из файла
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                old_monitors = {int(k): v for k, v in data.items()}
                
                # Мигрируем старые мониторинги в БД
                for user_id, config in old_monitors.items():
                    db_manager.save_monitor(user_id, config)
                    active_monitors[user_id] = config
                
                logger.info(f"Мигрировано {len(old_monitors)} мониторингов в БД")
                
    except Exception as e:
        logger.error(f"Не удалось загрузить мониторинги: {e}")

def save_active_monitors():
    """Сохранение активных мониторингов в базу данных и файл"""
    try:
        # Сохраняем в файл для совместимости
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(active_monitors, f, ensure_ascii=False, indent=2)
        
        # Мониторинги уже сохраняются в БД через db_manager.save_monitor()
        logger.debug("Мониторинги сохранены")
    except Exception as e:
        logger.error(f"Не удалось сохранить мониторинги: {e}")

def save_user_to_db(user_id: int, user_data: dict):
    """Сохраняет данные пользователя в базу данных"""
    try:
        return db_manager.save_user(user_id, user_data)
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя {user_id}: {e}")
        return False

def load_user_from_db(user_id: int) -> dict:
    """Загружает данные пользователя из базы данных"""
    try:
        return db_manager.get_user(user_id) or {}
    except Exception as e:
        logger.error(f"Ошибка загрузки пользователя {user_id}: {e}")
        return {}

def save_user_monitors_to_db(user_id: int):
    """Сохраняет мониторинги пользователя в БД"""
    try:
        if user_id in active_monitors:
            config = active_monitors[user_id]
            db_manager.save_monitor(user_id, config)
            return True
        return False
    except Exception as e:
        logger.error(f"Ошибка сохранения мониторинга пользователя {user_id}: {e}")
        return False

def load_user_monitors_from_db(user_id: int) -> list:
    """Загружает мониторинги пользователя из БД"""
    try:
        return db_manager.get_user_monitors(user_id)
    except Exception as e:
        logger.error(f"Ошибка загрузки мониторингов пользователя {user_id}: {e}")
        return []

# НЕ загружаем мониторинги на уровне модуля - переносим в main()
# load_active_monitors()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors from telegram.ext and log them."""
    # Получаем дополнительную информацию об update
    update_info = {}
    if hasattr(update, 'effective_user') and update.effective_user:
        update_info['user_id'] = update.effective_user.id
    if hasattr(update, 'effective_chat') and update.effective_chat:
        update_info['chat_id'] = update.effective_chat.id
    if hasattr(update, 'effective_message') and update.effective_message:
        update_info['message_id'] = update.effective_message.message_id
        
    safe_log_bot("Ошибка при обработке update", update_info, level="error")
    logger.error("Exception details:", exc_info=context.error)

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
            "minsk_smorgon": "🏙️ Минск → Сморгонь",
            "smorgon_minsk": "🏘️ Сморгонь → Минск",
            "ostrovets_smorgon": "🏘️ Островец → Сморгонь",
            "smorgon_ostrovets": "🏘️ Сморгонь → Островец",
            "both": "🔄 Оба направления",
            "all": "🔄 Все направления"
        }
        
        if direction in ["minsk_ostrovets", "ostrovets_minsk", "minsk_smorgon", "smorgon_minsk", 
                        "ostrovets_smorgon", "smorgon_ostrovets"]:
            webapp_url = create_webapp_url(direction, date)
            web_app = WebAppInfo(url=webapp_url)
            keyboard.append([
                InlineKeyboardButton(
                    f"🌐 Открыть сайт бронирования", 
                    web_app=web_app
                )
            ])
            
            # Добавляем специальную информацию для маршрутов через Сморгонь
            if "smorgon" in direction:
                keyboard.append([
                    InlineKeyboardButton("ℹ️ Информация о Сморгони", callback_data="smorgon_info")
                ])
                
        elif direction in ["both", "all"]:
            # Добавляем кнопки для множественных направлений
            webapp_url = create_webapp_url(direction, date)
            
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
    
    # Русские сокращения дней недели
    russian_weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    for i in range(7):  # Показываем 7 дней
        date = today + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        # Форматируем дату как dd.mm + день недели
        day_name = f"{date.strftime('%d.%m')} {russian_weekdays[date.weekday()]}"
        
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
        [InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors")],
        [InlineKeyboardButton("🌐 Открыть сайт", callback_data="open_website")]
    ]

    if bot_auth_manager.is_authenticated(user_id):
        # Пользователь вошел через улучшенную систему авторизации
        keyboard.append([InlineKeyboardButton("🎫 Забронировать билет", callback_data="book_ticket")])
        keyboard.append([InlineKeyboardButton("👤 Аккаунт (бета)", callback_data="account_beta")])
    else:
        # Пользователь не вошел
        keyboard.append([InlineKeyboardButton("🔒 Войти в аккаунт", callback_data="login_requests")])

    # Добавляем админ-панель для администратора
    if admin_panel and admin_panel.is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Функции администратора", callback_data="admin_panel")])

    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start"""
    text = (
        "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
        "🛣️ **Направления:** Минск ⇄ Островец\n\n"
        "💡 **Выберите действие:**"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_main_menu_keyboard(update.effective_user.id),
        parse_mode='Markdown'
    )

@callback_handler_protection(timeout=30)
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню - универсальный для всех conversation"""
    query = update.callback_query
    await safe_answer_callback(query)
    user_id = query.from_user.id

    # Очищаем состояние пользователя из хранилища
    if user_id in user_data_store:
        del user_data_store[user_id]
    
    # Очищаем состояние в context
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
        parse_mode='Markdown'
    )
    
    # ВАЖНО: Завершаем conversation state
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена любой conversation и переход в главное меню"""
    return await handle_main_menu(update, context)

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
            await safe_edit_message(
                update.callback_query,
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
            await safe_edit_message(
                update.callback_query,
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
            await safe_edit_message(
                update.callback_query,
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
            await safe_edit_message(
                update.callback_query,
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
    
    # Очищаем любые предыдущие состояния
    if user_id in user_data_store:
        del user_data_store[user_id]
    context.user_data.clear()
    
    # Инициализируем данные пользователя
    user_data_store[user_id] = {}
    
    text = (
        "🔔 **Настройка мониторинга рейсов**\n\n"
        "Я буду проверять появление мест каждые 5 минут и уведомлять вас!\n\n"
        "📅 **Шаг 1:** Выберите дату поездки:"
    )
    
    # Проверяем, это callback query или обычное сообщение
    if update.callback_query:
        await safe_edit_message(
                update.callback_query,
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

@callback_handler_protection(timeout=20)
async def handle_date_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора даты"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("date_"):
        selected_date = data.replace("date_", "")
        user_data_store[user_id]['date'] = selected_date
        
        # Проверяем, есть ли уже выбранный маршрут (поиск по городам)
        user_data = user_data_store.get(user_id, {})
        if user_data.get('from_city') and user_data.get('to_city'):
            # Маршрут уже выбран через города - сразу запускаем поиск
            from_city = user_data['from_city']
            to_city = user_data['to_city']
            
            await safe_edit_message(
                query,
                f"🔍 **Поиск маршрутов...**\n\n"
                f"📍 **Маршрут:** {from_city} → {to_city}\n"
                f"📅 **Дата:** {selected_date}",
                parse_mode='Markdown'
            )
            
            # Запускаем поиск маршрутов
            await perform_route_search(query, user_id, from_city, to_city, selected_date)
            return ConversationHandler.END
        else:
            # Обычный поток - выбираем направление
            await safe_edit_message(
                query,
                f"✅ **Выбрана дата:** {selected_date}\n\n"
                "🛣️ **Шаг 2:** Выберите направление:",
                reply_markup=get_direction_keyboard(),
                parse_mode='Markdown'
            )
            
            return CHOOSE_DIRECTION
    
    elif data == "custom_date":
        await safe_edit_message(
                query,
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
        
        await safe_edit_message(
                query,
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
    # Очищаем любые предыдущие состояния
    user_id = update.effective_user.id
    if user_id in user_data_store:
        del user_data_store[user_id]
    context.user_data.clear()
    
    await safe_answer_callback(update.callback_query)
    await safe_edit_message(
                update.callback_query,
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
            # Сохраняем данные пользователя в БД
            user_data = {
                'user_id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'last_name': update.effective_user.last_name,
                'phone': phone,
                'profile_data': {
                    'phone': phone,
                    'auth_method': 'requests_auth',
                    'last_login': datetime.now().isoformat()
                }
            }
            save_user_to_db(user_id, user_data)
            
            # Сохраняем сессию авторизации
            session_data = {
                'phone': phone,
                'auth_method': 'requests_auth',
                'login_time': datetime.now().isoformat(),
                'authenticated': True
            }
            db_manager.save_auth_session(user_id, phone, session_data)
            
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
            safe_log_system(f"Пользователь {user_id} успешно авторизован", {
                "user_id": user_id,
                "auth_method": "requests_auth",
                "status": "success"
            })
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
            safe_log_system(f"Неуспешная авторизация пользователя {user_id}", {
                "user_id": user_id,
                "auth_method": "requests_auth",
                "status": "failed",
                "reason": "invalid_credentials"
            })
    
    except Exception as e:
        safe_log_system(f"Ошибка авторизации пользователя {user_id}", {
            "user_id": user_id,
            "auth_method": "requests_auth",
            "status": "error",
            "error": str(e)
        }, level="error")
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
            await safe_answer_callback(update.callback_query, "❌ Сначала нужно войти в аккаунт!", show_alert=True)
            await safe_edit_message(
                update.callback_query,
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
        await safe_answer_callback(update.callback_query, "📋 Загружаю профиль...")

    try:
        # Загружаем данные пользователя из БД
        user_db_data = load_user_from_db(user_id)
        
        # Получаем профиль через новый менеджер
        profile = bot_auth_manager.get_user_profile(user_id)
        
        if profile:
            # Обновляем данные профиля в БД
            if user_db_data:
                user_db_data['profile_data'] = {
                    'name': profile.name,
                    'surname': profile.surname,
                    'patronymic': profile.patronymic,
                    'email': profile.email,
                    'phone': profile.phone,
                    'birth_date': profile.birth_date,
                    'passport_series': profile.passport_series,
                    'card_number': profile.card_number,
                    'last_profile_update': datetime.now().isoformat()
                }
                save_user_to_db(user_id, user_db_data)
            
            profile_text = format_profile_message(profile)
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="profile_requests")],
                [InlineKeyboardButton("🎫 Мои бронирования", callback_data="tickets_requests")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
            ]
            
            if update.callback_query:
                await safe_edit_message(update.callback_query,
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
                await safe_edit_message(update.callback_query,
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
            await safe_edit_message(update.callback_query,
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
            await safe_answer_callback(update.callback_query, "❌ Сначала нужно войти в аккаунт!", show_alert=True)
            await safe_edit_message(
                update.callback_query,
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
        await safe_answer_callback(update.callback_query, "🎫 Загружаю бронирования...")

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
            await safe_edit_message(
                update.callback_query,
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
            await safe_edit_message(
                update.callback_query,
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
                await safe_answer_callback(update.callback_query, "✅ Выход выполнен")
                await safe_edit_message(
                update.callback_query,
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
                await safe_answer_callback(update.callback_query, "❌ Ошибка при выходе", show_alert=True)
            logger.error(f"Ошибка при выходе пользователя {user_id}")
    else:
        if update.callback_query:
            await safe_answer_callback(update.callback_query, "❌ Вы не были авторизованы", show_alert=True)
            await safe_edit_message(
                update.callback_query,
                "ℹ️ **Вы не были авторизованы в системе**\n\n"
                "💡 Используйте кнопку \"🔒 Войти в аккаунт\" для входа",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='Markdown'
            )

@callback_handler_protection(timeout=20)
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
        
        await safe_edit_message(
                query,
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
        
        await safe_edit_message(
                query,
            error_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ==================== MONITORING HANDLERS ====================

@callback_handler_protection(timeout=20)
async def handle_monitoring_direction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора направления для мониторинга"""
    query = update.callback_query
    await safe_answer_callback(query)
    
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
        
        await safe_edit_message(
                query,
            f"✅ **Направление:** {direction_text}\n\n"
            "⏰ **Шаг 3:** Что важнее для вас?",
            reply_markup=get_time_type_keyboard(),
            parse_mode='Markdown'
        )
        
        return CHOOSE_TIME_TYPE
        
    elif data == "back_to_date":
        # Возвращаемся к выбору даты
        await safe_edit_message(
                query,
            "📅 **Шаг 1:** Выберите дату поездки:",
            reply_markup=get_date_keyboard(),
            parse_mode='Markdown'
        )
        
        return CHOOSE_DATE
    
    return CHOOSE_DIRECTION

@callback_handler_protection(timeout=20)
async def handle_time_type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа времени"""
    query = update.callback_query
    await safe_answer_callback(query)
    
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
            
            await safe_edit_message(
                query,
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
            await safe_edit_message(
                query,
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
        
        await safe_edit_message(
                query,
            f"✅ **Направление:** {direction_text}\n\n"
            "🛣️ **Шаг 2:** Выберите направление:",
            reply_markup=get_direction_keyboard(),
            parse_mode='Markdown'
        )
        
        return CHOOSE_DIRECTION
    
    return CHOOSE_TIME_TYPE

@callback_handler_protection(timeout=20)
async def handle_time_range_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора диапазона времени"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "back_to_range_list":
        # Возвращаемся к выбору диапазона из списка
        time_type = user_data_store[user_id].get('time_type', 'departure')
        await safe_edit_message(
                query,
            "🕐 **Шаг 4:** Выберите желаемый диапазон времени:",
            reply_markup=get_time_range_keyboard(time_type),
            parse_mode='Markdown'
        )
        return CHOOSE_TIME_RANGE
    
    elif data == "back_to_time_range":
        # Возвращаемся к выбору диапазона времени
        time_type = user_data_store[user_id].get('time_type', 'departure')
        await safe_edit_message(
                query,
            "🕐 **Шаг 4:** Выберите желаемый диапазон времени:",
            reply_markup=get_time_range_keyboard(time_type),
            parse_mode='Markdown'
        )
        return CHOOSE_TIME_RANGE
    
    elif data.startswith("range_"):
        time_range = data.replace("range_", "")
        
        if time_range == "custom":
            await safe_edit_message(
                query,
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
            
            await safe_edit_message(
                query,
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

@callback_handler_protection(timeout=25)
async def handle_monitoring_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения мониторинга"""
    query = update.callback_query
    await safe_answer_callback(query)
    
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
        
        # Сохраняем мониторинг в БД
        db_manager.save_monitor(user_id, config)
        
        # Добавляем задачу в планировщик
        if job_queue:
            job_queue.run_repeating(
                check_routes_for_user,
                interval=300,  # 5 минут в секундах
                first=10,      # Первый запуск через 10 секунд
                name=f"monitor_{user_id}",
                data=user_id
            )
        
        await safe_edit_message(
                query,
            "🎉 **Мониторинг запущен!**\n\n"
            f"{format_monitor_config(config)}\n\n"
            "✅ Я буду проверять наличие мест каждые 5 минут\n"
            "📱 Уведомления придут как только появятся подходящие рейсы\n\n"
            "💡 Используйте главное меню для управления:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
            ]]),
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    elif data == "confirm_no":
        await safe_edit_message(
                query,
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
    
    # Проверяем состояния бронирования
    current_state = context.user_data.get('state')
    
    if current_state == BOOKING_PASSENGER_NAME:
        await handle_booking_passenger_name(update, context)
        return
    elif current_state == BOOKING_PASSENGER_PHONE:
        await handle_booking_passenger_phone(update, context)
        return
    
    # Проверяем, что пользователь находится в процессе настройки мониторинга
    if user_id not in user_data_store:
        # Обычный поиск рейсов
        await handle_regular_search(update, context)
        return
    
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
    
    # Ввод диапазона времени (только когда ожидается ввод времени)
    elif re.match(r'^\d{2}:\d{2}-\d{2}:\d{2}$', text):
        # Проверяем валидность времени
        try:
            time_parts = text.split('-')
            start_time = time_parts[0]
            end_time = time_parts[1]
            
            # Проверяем формат времени
            start_hour, start_min = map(int, start_time.split(':'))
            end_hour, end_min = map(int, end_time.split(':'))
            
            if not (0 <= start_hour <= 23 and 0 <= start_min <= 59 and 
                   0 <= end_hour <= 23 and 0 <= end_min <= 59):
                raise ValueError("Неверное время")
            
            # Проверяем, что начальное время меньше конечного
            if start_hour * 60 + start_min >= end_hour * 60 + end_min:
                await update.message.reply_text(
                    "❌ **Ошибка в диапазоне времени**\n\n"
                    "Время начала должно быть раньше времени окончания.\n"
                    "Введите корректный диапазон в формате ЧЧ:ММ-ЧЧ:ММ",
                    parse_mode='Markdown'
                )
                return CHOOSE_TIME_RANGE
            
            user_data_store[user_id]['time_range'] = text
            
            config_text = format_monitor_config(user_data_store[user_id])
            
            await update.message.reply_text(
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
            
        except ValueError:
            await update.message.reply_text(
                "❌ **Неверный формат времени**\n\n"
                "Используйте формат ЧЧ:ММ-ЧЧ:ММ, например:\n"
                "• `07:00-09:00` - с 7 до 9 утра\n"
                "• `17:30-19:30` - с 17:30 до 19:30\n\n"
                "Убедитесь, что часы от 00 до 23, минуты от 00 до 59.",
                parse_mode='Markdown'
            )
            return CHOOSE_TIME_RANGE
    
    else:
        # Если формат не подходит ни под один из ожидаемых, показываем подсказку
        if user_id in user_data_store:
            # Проверяем какой именно ввод ожидается
            if 'date' not in user_data_store[user_id]:
                await update.message.reply_text(
                    "❌ **Неверный формат**\n\n"
                    "Ожидается дата в формате YYYY-MM-DD, например: `2025-01-15`",
                    parse_mode='Markdown'
                )
                return CHOOSE_DATE
            elif user_data_store[user_id].get('time_type') and 'time_range' not in user_data_store[user_id]:
                await update.message.reply_text(
                    "❌ **Неверный формат времени**\n\n"
                    "Ожидается диапазон времени в формате ЧЧ:ММ-ЧЧ:ММ, например:\n"
                    "• `07:00-09:00`\n"
                    "• `17:30-19:30`",
                    parse_mode='Markdown'
                )
                return CHOOSE_TIME_RANGE
        
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
            [InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors")]
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

@callback_handler_protection(timeout=15)
async def handle_direction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора направления для поиска"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = query.from_user.id
    data = query.data
    
    # Сохраняем выбранное направление
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    
    user_data_store[user_id]['search_direction'] = data.replace('search_dir_', '')
    
    # Показываем календарь для выбора даты
    keyboard = get_date_keyboard()
    
    await safe_edit_message(
                query,
        "📅 **Выберите дату для поиска рейсов:**",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    return SEARCH_DATE

@callback_handler_protection(timeout=30)
async def handle_search_with_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка поиска с выбранным направлением и датой"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = query.from_user.id
    date = query.data.replace('date_', '')
    
    user_data = user_data_store.get(user_id, {})
    
    # Проверяем, выбран ли маршрут по отдельным городам
    if user_data.get('route_selected'):
        from_city = user_data.get('from_city')
        to_city = user_data.get('to_city')
        
        await safe_edit_message(
                query,
            f"🔍 **Ищу рейсы {from_city} → {to_city} на {date}...**",
            parse_mode='Markdown'
        )
        
        try:
            await init_parser()
            
            # Определяем направление для парсера
            direction_map = {
                ("Минск", "Островец"): "minsk_to_ostrovets",
                ("Островец", "Минск"): "ostrovets_to_minsk", 
                ("Минск", "Сморгонь"): "minsk_to_smorgon",
                ("Сморгонь", "Минск"): "smorgon_to_minsk",
                ("Островец", "Сморгонь"): "ostrovets_to_smorgon",
                ("Сморгонь", "Островец"): "smorgon_to_ostrovets"
            }
            
            routes_key = direction_map.get((from_city, to_city))
            
            if routes_key:
                # Получаем конкретные маршруты
                routes_data = await parser.get_all_routes(date)
                
                # Создаем упрощенную структуру для форматирования
                simple_routes_data = {
                    routes_key: routes_data.get(routes_key, []),
                    'success': routes_data.get('success', False)
                }
                
                # Форматируем сообщение для конкретного направления
                if simple_routes_data[routes_key]:
                    message_parts = [f"📅 **Рейсы {from_city} → {to_city} на {date}**", ""]
                    
                    for i, route in enumerate(simple_routes_data[routes_key][:8], 1):
                        seats = route.get('available_seats', 0)
                        
                        time_info = f"**{route.get('departure_time')} → {route.get('arrival_time')}**"
                        duration = route.get('duration', 'н/д')
                        
                        message_parts.append(f"{i}. {time_info} ({duration})")
                        
                        # Проверяем, нужно ли показывать места
                        is_smorgon_to_ostrovets = (from_city == "Сморгонь" and to_city == "Островец")
                        
                        if not is_smorgon_to_ostrovets and seats is not None:
                            seat_emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
                            message_parts.append(f"   {seat_emoji} {seats} мест")
                        elif is_smorgon_to_ostrovets:
                            message_parts.append(f"   ✅ Всех берут")
                        
                        # Добавляем информацию о промежуточных городах
                        if route.get('via_smorgon'):
                            message_parts.append(f"   🛣️ *через Сморгонь*")
                        elif route.get('via_oshmiany'):
                            message_parts.append(f"   🛣️ *через Ошмяны*")
                    
                    message_parts.append(f"\n📊 **Всего рейсов:** {len(simple_routes_data[routes_key])}")
                    message = "\n".join(message_parts)
                else:
                    message = f"❌ **Рейсы {from_city} → {to_city} на {date} не найдены**"
                
                # Очищаем данные пользователя
                user_data_store[user_id] = {}
                
            else:
                message = "❌ **Неподдерживаемое направление**"
            
            # Создаем клавиатуру
            keyboard_buttons = [
                [InlineKeyboardButton("🔍 Новый поиск", callback_data="search_routes")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            
            await safe_edit_message(
                query,
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
            
        except Exception as e:
            logger.error(f"Ошибка поиска рейсов: {e}")
            await safe_edit_message(
                query,
                "❌ **Ошибка поиска рейсов**\n\nПопробуйте позже.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Повторить поиск", callback_data="search_routes")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
        
        return
    
    # Старая логика для готовых направлений
    direction = user_data.get('search_direction', 'all')
    
    await safe_edit_message(
                query,
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
        
        await safe_edit_message(
                query,
            message,
            parse_mode='Markdown',
            reply_markup=webapp_keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка поиска рейсов: {e}")
        await safe_edit_message(
                query,
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

async def perform_route_search(query, user_id: int, from_city: str, to_city: str, date: str):
    """Выполняет поиск маршрутов для выбранных городов и даты"""
    try:
        await init_parser()
        
        # Определяем направление для парсера
        direction_map = {
            ("Минск", "Островец"): "minsk_to_ostrovets",
            ("Островец", "Минск"): "ostrovets_to_minsk",
            ("Минск", "Сморгонь"): "minsk_to_smorgon",
            ("Сморгонь", "Минск"): "smorgon_to_minsk",
            ("Островец", "Сморгонь"): "ostrovets_to_smorgon",
            ("Сморгонь", "Островец"): "smorgon_to_ostrovets"
        }
        
        routes_key = direction_map.get((from_city, to_city))
        
        if routes_key:
            # Получаем конкретные маршруты
            routes_data = await parser.get_all_routes(date)
            
            # Создаем упрощенную структуру для форматирования
            simple_routes_data = {
                routes_key: routes_data.get(routes_key, []),
                'success': routes_data.get('success', False)
            }
            
            # Форматируем сообщение для конкретного направления
            if simple_routes_data[routes_key]:
                message_parts = [f"📅 **Рейсы {from_city} → {to_city} на {date}**", ""]
                
                for i, route in enumerate(simple_routes_data[routes_key][:8], 1):
                    seats = route.get('available_seats', 0)
                    
                    time_info = f"**{route.get('departure_time')} → {route.get('arrival_time')}**"
                    duration = route.get('duration', 'н/д')
                    
                    message_parts.append(f"{i}. {time_info} ({duration})")
                    
                    # Проверяем, нужно ли показывать места
                    is_smorgon_to_ostrovets = (from_city == "Сморгонь" and to_city == "Островец")
                    
                    if not is_smorgon_to_ostrovets and seats is not None:
                        seat_emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
                        message_parts.append(f"   {seat_emoji} {seats} мест")
                    elif is_smorgon_to_ostrovets:
                        message_parts.append(f"   ✅ Всех берут")
                    
                    # Добавляем информацию о промежуточных городах
                    if route.get('via_smorgon'):
                        message_parts.append(f"   🛣️ *через Сморгонь*")
                    elif route.get('via_oshmiany'):
                        message_parts.append(f"   🛣️ *через Ошмяны*")
                    
                    message_parts.append("")  # Пустая строка между маршрутами
                
                message = "\n".join(message_parts)
                
                # Добавляем информацию о промежуточных маршрутах для Сморгони
                if from_city == "Сморгонь" or to_city == "Сморгонь":
                    message += "\n💡 *Маршруты через Сморгонь могут включать пересадки*"
                
            else:
                message = f"❌ **Рейсы {from_city} → {to_city} на {date} не найдены**\n\n"
                message += "Попробуйте:\n"
                message += "• Выбрать другую дату\n"
                message += "• Проверить доступность маршрута\n"
                
                if from_city == "Сморгонь" or to_city == "Сморгонь":
                    message += "• Поискать транзитные рейсы через Минск"
        else:
            message = f"❌ **Направление {from_city} → {to_city} не поддерживается**"
        
        # Создаем клавиатуру для продолжения
        keyboard = [
            [InlineKeyboardButton("🔍 Новый поиск", callback_data="search_routes")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        
        await safe_edit_message(
                query,
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка поиска маршрутов {from_city} → {to_city}: {e}")
        await safe_edit_message(
                query,
            f"❌ **Ошибка поиска рейсов {from_city} → {to_city}**\n\n"
            "Попробуйте позже или выберите другое направление.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="search_by_cities")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
    
    # Очищаем данные пользователя
    if user_id in user_data_store:
        user_data_store[user_id].pop('from_city', None)
        user_data_store[user_id].pop('to_city', None)
        user_data_store[user_id].pop('date', None)
        user_data_store[user_id].pop('route_selected', None)

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

async def emergency_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экстренный сброс состояния пользователя"""
    user_id = update.effective_user.id
    
    try:
        # Выполняем экстренный сброс
        await emergency_conversation_reset(user_id, context)
        
        # Показываем статистику до очистки
        had_active_callback = user_id in active_callbacks
        had_user_data = bool(context.user_data)
        had_stored_data = user_id in user_data_store
        
        reset_info = []
        if had_active_callback:
            reset_info.append("📞 Активный callback")
        if had_user_data:
            reset_info.append("💾 Данные context")
        if had_stored_data:
            reset_info.append("🗃️ Сохраненные данные")
        
        if reset_info:
            status_text = "Очищено: " + ", ".join(reset_info)
        else:
            status_text = "Состояние уже было чистым"
            
        text = (
            "🚨 **Экстренный сброс выполнен**\n\n"
            f"👤 **Пользователь:** {user_id}\n"
            f"🧹 **Статус:** {status_text}\n\n"
            "✅ Все состояния сброшены. Бот готов к работе!"
        )
        
        # Отправляем с главным меню
        await update.message.reply_text(
            text,
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
        
        logger.info(f"🚨 [{user_id}] Экстренный сброс выполнен по команде /reset")
        
    except Exception as e:
        logger.error(f"Ошибка в emergency_reset_command: {e}")
        await update.message.reply_text(
            "❌ Ошибка при выполнении экстренного сброса. Попробуйте перезапустить бота командой /start"
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
    """Начало процесса поиска рейсов с выбором направления"""
    # Создаем клавиатуру для выбора типа поиска
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("�️ Минск → Островец", callback_data="search_dir_minsk_ostrovets")],
        [InlineKeyboardButton("🏘️ Островец → Минск", callback_data="search_dir_ostrovets_minsk")],
        [InlineKeyboardButton("🎯 Выбрать города по отдельности", callback_data="search_by_cities")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    if update.message:
        await update.message.reply_text(
            "🔍 **Выберите маршрут для поиска:**\n\n"
            "�️🏘️ **Популярные направления** - быстрый доступ к самым популярным маршрутам\n"
            "🎯 **По отдельности** - выберите откуда и куда, включая Сморгонь",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        query = update.callback_query
        await safe_edit_message(
                query,
            "🔍 **Выберите маршрут для поиска:**\n\n"
            "🏙️�️ **Популярные направления** - быстрый доступ к самым популярным маршрутам\n"
            "🎯 **По отдельности** - выберите откуда и куда, включая Сморгонь",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def handle_search_by_cities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало поиска с выбором городов по отдельности"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    # Создаем клавиатуру для выбора города отправления
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙️ Минск", callback_data="from_city_Минск")],
        [InlineKeyboardButton("🏘️ Островец", callback_data="from_city_Островец")],
        [InlineKeyboardButton("🏙️ Сморгонь", callback_data="from_city_Сморгонь")],
        [InlineKeyboardButton("🔙 Назад", callback_data="search_routes")]
    ])
    
    await safe_edit_message(
                query,
        "📍 **Выберите город отправления:**",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def handle_from_city_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора города отправления"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = query.from_user.id
    from_city = query.data.replace('from_city_', '')
    
    # Сохраняем выбранный город отправления
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    user_data_store[user_id]['from_city'] = from_city
    
    # Создаем клавиатуру для выбора города назначения (исключаем выбранный город)
    keyboard_buttons = []
    
    cities = ["Минск", "Островец", "Сморгонь"]
    city_emojis = {"Минск": "🏙️", "Островец": "🏘️", "Сморгонь": "🏙️"}
    
    for city in cities:
        if city != from_city:
            keyboard_buttons.append([InlineKeyboardButton(
                f"{city_emojis[city]} {city}", 
                callback_data=f"to_city_{city}"
            )])
    
    keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="search_by_cities")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    await safe_edit_message(
                query,
        f"📍 **Откуда:** {from_city}\n"
        f"📍 **Выберите город назначения:**",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def handle_to_city_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора города назначения"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = query.from_user.id
    to_city = query.data.replace('to_city_', '')
    
    # Получаем город отправления
    user_data = user_data_store.get(user_id, {})
    from_city = user_data.get('from_city')
    
    if not from_city:
        await safe_edit_message(
                query,
            "❌ Ошибка: город отправления не выбран. Попробуйте снова.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Начать заново", callback_data="search_routes")
            ]])
        )
        return
    
    # Сохраняем выбранный маршрут
    user_data_store[user_id]['to_city'] = to_city
    user_data_store[user_id]['route_selected'] = True
    
    # Показываем календарь для выбора даты
    keyboard = get_date_keyboard()
    
    await safe_edit_message(
                query,
        f"📍 **Маршрут:** {from_city} → {to_city}\n"
        f"📅 **Выберите дату для поиска рейсов:**",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    return SEARCH_DATE

async def handle_search_by_directions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка поиска по готовым направлениям (старый метод)"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    # Создаем клавиатуру для выбора направления
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙️ Минск → Островец", callback_data="search_dir_minsk_ostrovets")],
        [InlineKeyboardButton("🏘️ Островец → Минск", callback_data="search_dir_ostrovets_minsk")],
        [InlineKeyboardButton("🏙️ Минск → Сморгонь", callback_data="search_dir_minsk_smorgon")],
        [InlineKeyboardButton("🏘️ Сморгонь → Минск", callback_data="search_dir_smorgon_minsk")],
        [InlineKeyboardButton("🏘️ Островец → Сморгонь", callback_data="search_dir_ostrovets_smorgon")],
        [InlineKeyboardButton("🏘️ Сморгонь → Островец", callback_data="search_dir_smorgon_ostrovets")],
        [InlineKeyboardButton("🔄 Все направления", callback_data="search_dir_all")],
        [InlineKeyboardButton("🔙 Назад", callback_data="search_routes")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    await safe_edit_message(
                query,
        "🛣️ **Выберите направление для поиска:**\n\n"
        "🚌 **Основные маршруты:**\n"
        "• Минск ↔ Островец\n\n"
        "🏙️ **Маршруты через Сморгонь:**\n"
        "• Минск ↔ Сморгонь\n"
        "• Островец ↔ Сморгонь\n\n"
        "💡 *Маршруты через Сморгонь включают транзитные рейсы*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    return SEARCH_FROM

def format_routes_message(routes_data, date, direction='all'):
    """Форматирование сообщения с рейсами"""
    if not routes_data.get('success', False):
        return "❌ **Не удалось получить данные**"
    
    # Получаем данные для всех направлений
    minsk_to_ostrovets = routes_data.get('minsk_to_ostrovets', [])[:8]
    ostrovets_to_minsk = routes_data.get('ostrovets_to_minsk', [])[:8]
    minsk_to_smorgon = routes_data.get('minsk_to_smorgon', [])[:8]
    smorgon_to_minsk = routes_data.get('smorgon_to_minsk', [])[:8]
    ostrovets_to_smorgon = routes_data.get('ostrovets_to_smorgon', [])[:8]
    smorgon_to_ostrovets = routes_data.get('smorgon_to_ostrovets', [])[:8]
    
    # Определяем направление из данных direction
    direction_mapping = {
        'search_dir_minsk_ostrovets': 'minsk_ostrovets',
        'search_dir_ostrovets_minsk': 'ostrovets_minsk',
        'search_dir_minsk_smorgon': 'minsk_smorgon',
        'search_dir_smorgon_minsk': 'smorgon_minsk',
        'search_dir_ostrovets_smorgon': 'ostrovets_smorgon',
        'search_dir_smorgon_ostrovets': 'smorgon_ostrovets',
        'search_dir_both': 'both',
        'search_dir_all': 'all'
    }
    
    if direction in direction_mapping:
        direction = direction_mapping[direction]
    
    parts = [f"📅 **Рейсы на {date}**", ""]
    
    def format_route_section(routes, title, emoji="🚌"):
        """Форматирует секцию маршрутов"""
        if not routes:
            return []
            
        section = [f"{emoji} **{title}:**"]
        
        for i, route in enumerate(routes, 1):
            seats = route.get('available_seats', 0)
            
            # Форматируем основную информацию
            time_info = f"**{route.get('departure_time')} → {route.get('arrival_time')}**"
            duration = route.get('duration', 'н/д')
            
            section.append(f"{i}. {time_info} ({duration})")
            
            # Проверяем, нужно ли показывать места (для Сморгонь-Островец не показываем)
            from_city = route.get('from_city', '')
            to_city = route.get('to_city', '')
            is_smorgon_to_ostrovets = (from_city == "Сморгонь" and to_city == "Островец")
            
            if not is_smorgon_to_ostrovets and seats is not None:
                seat_emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
                section.append(f"   {seat_emoji} {seats} мест")
            elif is_smorgon_to_ostrovets:
                section.append(f"   ✅ Всех берут")
            
            # Добавляем информацию о промежуточных городах для транзитных маршрутов
            if route.get('via_smorgon'):
                section.append(f"   🛣️ *через Сморгонь*")
            elif route.get('via_oshmiany'):
                section.append(f"   🛣️ *через Ошмяны*")
                
        return section
    
    # Показываем рейсы в зависимости от выбранного направления
    if direction == 'minsk_ostrovets':
        parts.extend(format_route_section(minsk_to_ostrovets, "Минск → Островец"))
        parts.append(f"\n📊 **Всего рейсов:** {len(minsk_to_ostrovets)}")
        
    elif direction == 'ostrovets_minsk':
        parts.extend(format_route_section(ostrovets_to_minsk, "Островец → Минск"))
        parts.append(f"\n📊 **Всего рейсов:** {len(ostrovets_to_minsk)}")
        
    elif direction == 'minsk_smorgon':
        parts.extend(format_route_section(minsk_to_smorgon, "Минск → Сморгонь", "🏙️"))
        if minsk_to_smorgon:
            parts.append("\n💡 *Включены транзитные рейсы до Островца*")
        parts.append(f"\n📊 **Всего рейсов:** {len(minsk_to_smorgon)}")
        
    elif direction == 'smorgon_minsk':
        parts.extend(format_route_section(smorgon_to_minsk, "Сморгонь → Минск", "🏘️"))
        if smorgon_to_minsk:
            parts.append("\n💡 *Включены транзитные рейсы из Островца*")
        parts.append(f"\n📊 **Всего рейсов:** {len(smorgon_to_minsk)}")
        
    elif direction == 'ostrovets_smorgon':
        parts.extend(format_route_section(ostrovets_to_smorgon, "Островец → Сморгонь", "🏘️"))
        if ostrovets_to_smorgon:
            parts.append("\n💡 *Включены транзитные рейсы до Минска*")
        parts.append(f"\n📊 **Всего рейсов:** {len(ostrovets_to_smorgon)}")
        
    elif direction == 'smorgon_ostrovets':
        parts.extend(format_route_section(smorgon_to_ostrovets, "Сморгонь → Островец", "🏘️"))
        if smorgon_to_ostrovets:
            parts.append("\n💡 *Включены транзитные рейсы из Минска*")
        parts.append(f"\n📊 **Всего рейсов:** {len(smorgon_to_ostrovets)}")
        
    elif direction == 'both':
        # Показываем основные направления
        if minsk_to_ostrovets:
            parts.extend(format_route_section(minsk_to_ostrovets, "Минск → Островец"))
            parts.append("")
        
        if ostrovets_to_minsk:
            parts.extend(format_route_section(ostrovets_to_minsk, "Островец → Минск"))
            parts.append("")
        
        total = len(minsk_to_ostrovets) + len(ostrovets_to_minsk)
        parts.append(f"📊 **Всего рейсов:** {total}")
        
    elif direction == 'all':
        # Показываем все направления
        all_routes = []
        
        if minsk_to_ostrovets:
            parts.extend(format_route_section(minsk_to_ostrovets, "Минск → Островец"))
            parts.append("")
            all_routes.extend(minsk_to_ostrovets)
        
        if ostrovets_to_minsk:
            parts.extend(format_route_section(ostrovets_to_minsk, "Островец → Минск"))
            parts.append("")
            all_routes.extend(ostrovets_to_minsk)
        
        if minsk_to_smorgon:
            parts.extend(format_route_section(minsk_to_smorgon, "Минск → Сморгонь", "🏙️"))
            parts.append("")
            all_routes.extend(minsk_to_smorgon)
        
        if smorgon_to_minsk:
            parts.extend(format_route_section(smorgon_to_minsk, "Сморгонь → Минск", "🏘️"))
            parts.append("")
            all_routes.extend(smorgon_to_minsk)
        
        if ostrovets_to_smorgon:
            parts.extend(format_route_section(ostrovets_to_smorgon, "Островец → Сморгонь", "🏘️"))
            parts.append("")
            all_routes.extend(ostrovets_to_smorgon)
        
        if smorgon_to_ostrovets:
            parts.extend(format_route_section(smorgon_to_ostrovets, "Сморгонь → Островец", "🏘️"))
            parts.append("")
            all_routes.extend(smorgon_to_ostrovets)
        
        parts.append(f"📊 **Всего рейсов:** {len(all_routes)}")
        
        if any([minsk_to_smorgon, smorgon_to_minsk, ostrovets_to_smorgon, smorgon_to_ostrovets]):
            parts.append("\n💡 *Маршруты через Сморгонь включают транзитные рейсы*")
    else:
        parts.append("❌ **Рейсы не найдены для выбранного направления**")
    
    return "\n".join(parts)

# ==================== BOOKING HANDLERS ====================

async def book_ticket_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик запроса на бронирование билета."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Очищаем любые предыдущие состояния
    if user_id in user_data_store:
        del user_data_store[user_id]
    context.user_data.clear()
    
    # Проверяем, что пользователь авторизован
    if not bot_auth_manager.is_authenticated(user_id):
        await safe_edit_message(query,
            "❌ Для бронирования билетов необходимо войти в аккаунт",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔒 Войти в аккаунт", callback_data="login_requests")]])
        )
        return

    # Показываем интерфейс выбора маршрута
    await safe_edit_message(query,
        "🎫 **Бронирование билета**\n\n"
        "📅 Выберите дату поездки:",
        reply_markup=get_date_keyboard(),
        parse_mode='Markdown'
    )
    
    # Устанавливаем состояние для бронирования
    context.user_data['booking_mode'] = True

async def handle_booking_date_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора даты для бронирования."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not context.user_data.get('booking_mode'):
        return
    
    selected_date = query.data.replace("date_", "")
    context.user_data['booking_date'] = selected_date
    
    await safe_edit_message(query,
        f"🔍 **Поиск рейсов на {selected_date}...**",
        parse_mode='Markdown'
    )
    
    try:
        # Ищем доступные маршруты через менеджер авторизации
        # Получаем маршруты в обоих направлениях для бронирования
        routes_minsk_ostrovets = await bot_auth_manager.search_routes(user_id, "Минск", "Островец", selected_date)
        routes_ostrovets_minsk = await bot_auth_manager.search_routes(user_id, "Островец", "Минск", selected_date)
        
        # Объединяем все маршруты
        all_routes = []
        if routes_minsk_ostrovets:
            all_routes.extend(routes_minsk_ostrovets)
        if routes_ostrovets_minsk:
            all_routes.extend(routes_ostrovets_minsk)
        
        if not all_routes:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="book_ticket")]]
            await safe_edit_message(query,
                f"❌ На {selected_date} нет доступных рейсов для бронирования",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Формируем сообщение с доступными маршрутами
        message = f"🎫 **Доступные рейсы на {selected_date}:**\n\n"
        keyboard = []
        
        for i, route in enumerate(all_routes):
            message += f"🚌 **{route.departure_time}** - {route.from_location} → {route.to_location}\n"
            message += f"💰 Цена: {route.price}\n"
            if hasattr(route, 'available_seats') and route.available_seats:
                message += f"🪑 Мест: {route.available_seats}\n"
            message += "\n"
            
            keyboard.append([InlineKeyboardButton(
                f"🎫 {route.departure_time} - {route.from_location} → {route.to_location}",
                callback_data=f"booking_route_{i}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Выбрать другую дату", callback_data="book_ticket")])
        
        # Сохраняем маршруты в контексте
        context.user_data['available_routes'] = all_routes
        
        await safe_edit_message(query,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при поиске рейсов для бронирования: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="book_ticket")]]
        await safe_edit_message(query,
            "❌ Произошла ошибка при поиске рейсов. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_booking_passenger_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода данных пассажира."""
    if context.user_data.get('state') != BOOKING_PASSENGER_NAME:
        return
    
    passenger_name = update.message.text.strip()
    
    # Проверяем формат ФИО
    if len(passenger_name.split()) < 2:
        await update.message.reply_text(
            "❌ Пожалуйста, введите ФИО в формате: Фамилия Имя Отчество\n"
            "Например: Иванов Иван Иванович"
        )
        return
    
    context.user_data['passenger_name'] = passenger_name
    
    # Запрашиваем номер телефона
    await update.message.reply_text(
        "📱 Введите номер телефона пассажира:\n"
        "Формат: +375XXXXXXXXX\n\n"
        "Например: +375291234567"
    )
    context.user_data['state'] = BOOKING_PASSENGER_PHONE

async def handle_booking_passenger_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода номера телефона пассажира."""
    if context.user_data.get('state') != BOOKING_PASSENGER_PHONE:
        return
    
    passenger_phone = update.message.text.strip()
    
    # Простая проверка формата номера
    if not passenger_phone.startswith('+375') or len(passenger_phone) != 13:
        await update.message.reply_text(
            "❌ Пожалуйста, введите номер в формате: +375XXXXXXXXX\n"
            "Например: +375291234567"
        )
        return
    
    context.user_data['passenger_phone'] = passenger_phone
    
    # Показываем подтверждение
    route_id = context.user_data.get('selected_route_id')
    routes = context.user_data.get('available_routes', [])
    
    if route_id is not None and route_id.isdigit() and int(route_id) < len(routes):
        route = routes[int(route_id)]
        
        confirmation_text = (
            "✅ **Подтверждение бронирования**\n\n"
            f"📅 Дата: {context.user_data.get('booking_date')}\n"
            f"🚌 Рейс: {route.departure_time} - {route.from_station} → {route.to_station}\n"
            f"💰 Цена: {route.price}\n"
            f"👤 Пассажир: {context.user_data['passenger_name']}\n"
            f"📱 Телефон: {context.user_data['passenger_phone']}\n\n"
            "❓ Подтвердить бронирование?"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="booking_confirm")],
            [InlineKeyboardButton("❌ Отменить", callback_data="booking_cancel")]
        ]
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и выполнение бронирования."""
    query = update.callback_query
    user_id = query.from_user.id
    
    route_id = context.user_data.get('selected_route_id')
    routes = context.user_data.get('available_routes', [])
    
    if route_id is None or not route_id.isdigit() or int(route_id) >= len(routes):
        await safe_edit_message(
                query,
            "❌ Ошибка: не удалось найти выбранный маршрут",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]])
        )
        return
    
    route = routes[int(route_id)]
    
    # Создаем запрос на бронирование
    booking_request = BookingRequest(
        route_id=route.route_id if hasattr(route, 'route_id') else str(route_id),
        passenger_count=1,
        passenger_name=context.user_data['passenger_name'],
        passenger_phone=context.user_data['passenger_phone'],
        departure_date=context.user_data.get('booking_date', '')
    )
    
    await safe_edit_message(query,
        "⏳ Обрабатываю бронирование...",
        parse_mode='Markdown'
    )
    
    try:
        # Выполняем бронирование через менеджер авторизации
        result = await bot_auth_manager.book_ticket(user_id, booking_request)
        
        if result:
            # result это UserBooking, а не BookingResult
            confirmation_message = format_booking_confirmation(result)
            
            # Очищаем данные пользователя
            context.user_data.clear()
            
            await safe_edit_message(query,
                confirmation_message,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]),
                parse_mode='Markdown'
            )
        else:
            await safe_edit_message(query,
                "❌ Ошибка бронирования: не удалось создать бронирование",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data="book_ticket")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
            
    except Exception as e:
        logger.error(f"Ошибка при бронировании билета: {e}")
        await safe_edit_message(query,
            "❌ Произошла ошибка при бронировании. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="book_ticket")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ])
        )

# ==================== CALLBACK HANDLERS ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общий обработчик кнопок"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    # Sanitize callback data to prevent injection attacks
    data = security.sanitize_callback_data(query.data)
    user_id = query.from_user.id
    
    if data == "setup_monitoring":
        # Начинаем настройку мониторинга
        user_data_store[user_id] = {}
        
        await safe_edit_message(
                query,
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
            
            await safe_edit_message(
                query,
                "✅ **Мониторинг остановлен**\n\n"
                "💡 Для настройки нового мониторинга используйте /start",
                parse_mode='Markdown'
            )
        else:
            await safe_edit_message(
                query,
                "ℹ️ **Мониторинг не был активен**",
                parse_mode='Markdown'
            )
    
    elif data == "search_routes":
        # Новый поиск с выбором направления
        await handle_regular_search(update, context)
    
    elif data == "search_by_cities":
        # Поиск с выбором городов по отдельности
        await handle_search_by_cities(update, context)
    
    elif data.startswith("from_city_"):
        # Обработка выбора города отправления
        await handle_from_city_choice(update, context)
    
    elif data.startswith("to_city_"):
        # Обработка выбора города назначения
        await handle_to_city_choice(update, context)
    
    elif data == "smorgon_info":
        # Показываем информацию о Сморгони
        from src.utils.route_analyzer import RouteAnalyzer
        warning_message = RouteAnalyzer.generate_smorgon_warning()
        
        await safe_edit_message(query,
            warning_message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="search_routes")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
    
    elif data.startswith("search_dir_"):
        # Обработка выбора направления для поиска
        await handle_direction_choice(update, context)
    
    elif data.startswith("date_") and user_id in user_data_store and user_data_store[user_id].get('from_city') and user_data_store[user_id].get('to_city'):
        # Поиск с выбранными городами
        await handle_date_choice(update, context)
    
    elif data.startswith("date_") and context.user_data.get('booking_mode'):
        # Обработка выбора даты для бронирования
        await handle_booking_date_choice(update, context)
    
    elif data.startswith("date_") and user_id in user_data_store and 'search_direction' in user_data_store[user_id]:
        # Поиск с выбранным направлением и датой
        await handle_search_with_direction(update, context)
    
    elif data.startswith("date_") and user_id not in user_data_store:
        # Обычный поиск по дате
        selected_date = data.replace("date_", "")
        await safe_edit_message(query, f"🔍 **Ищу рейсы на {selected_date}...**", parse_mode='Markdown')
        
        try:
            await init_parser()
            routes_data = await parser.get_all_routes(selected_date)
            message = format_routes_message(routes_data, selected_date)
            
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
            
            await safe_edit_message(query,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            await safe_edit_message(query, "❌ **Ошибка при поиске рейсов**", parse_mode='Markdown')
    
    elif data == "back_to_main":
        # Очищаем данные пользователя при возврате в главное меню
        if user_id in user_data_store:
            del user_data_store[user_id]
        
        # Очищаем состояние в context
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
            parse_mode='Markdown'
        )
        
        # ВАЖНО: Завершаем conversation state для button_callback
        return ConversationHandler.END
    
    elif data == "login_requests":
        # Запускаем процесс входа - это обработается ConversationHandler
        await start_login_requests(update, context)
        return LOGIN_REQUESTS_PHONE
    
    elif data == "book_ticket":
        # Запускаем процесс бронирования билета
        await book_ticket_handler(update, context)
    
    elif data.startswith("booking_route_"):
        # Выбор маршрута для бронирования
        route_id = data.replace("booking_route_", "")
        context.user_data['selected_route_id'] = route_id
        
        # Показываем форму для ввода данных пассажира
        keyboard = [[InlineKeyboardButton("🔙 Назад к поиску", callback_data="book_ticket")]]
        await safe_edit_message(
                query,
            "👤 Введите данные пассажира:\n"
            "Формат: Фамилия Имя Отчество\n\n"
            "Например: Иванов Иван Иванович",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['state'] = BOOKING_PASSENGER_NAME
        
    elif data == "booking_confirm":
        # Подтверждение бронирования
        await confirm_booking(update, context)
        
    elif data == "booking_cancel":
        # Отмена бронирования
        text = get_greeting_message(query.from_user)
        await safe_edit_message(
                query,text, reply_markup=get_main_menu_keyboard(user_id))
    
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
    
    elif data == "my_monitors":
        if user_id in active_monitors:
            config = active_monitors[user_id]
            config_text = format_monitor_config(config)
            
            keyboard = [
                [InlineKeyboardButton("🛑 Остановить", callback_data="stop_monitoring")],
                [InlineKeyboardButton("🔧 Изменить", callback_data="setup_monitoring")],
                [InlineKeyboardButton("📱 Проверить сейчас", callback_data="check_now")]
            ]
            
            await safe_edit_message(
                query,
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
            
            await safe_edit_message(
                query,
                "📊 **Мониторинг не активен**\n\n"
                "💡 Хотите настроить автоматическую проверку рейсов?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    elif data == "check_now":
        if user_id in active_monitors:
            await safe_answer_callback(query, "🔍 Проверяю рейсы...")
            
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
            
            await safe_edit_message(
                query,
                "✅ **Проверка завершена**\n\n"
                "Если найдены подходящие рейсы, вы получите уведомление.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                ]]),
                parse_mode='Markdown'
            )
        else:
            await safe_answer_callback(query, "❌ Мониторинг не активен")
    
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
        await safe_edit_message(
                query,
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
    
    elif data == "open_website":
        # Обработчик открытия сайта
        await safe_edit_message(
                query,
            "🌐 **Официальный сайт маршруточки**\n\n"
            "Вы можете посетить официальный сайт для бронирования билетов:\n\n"
            "🔗 **[билет.маршруточка.бел](https://билет.маршруточка.бел/)**\n\n"
            "💡 Нажмите на ссылку выше или используйте веб-приложение ниже:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Открыть веб-приложение", web_app=WebAppInfo(url="https://билет.маршруточка.бел/"))],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
    
    elif data == "account_beta":
        # Обработчик меню аккаунта (бета)
        await handle_account_beta_menu(update, context)
    
    # Проверяем callback data, которые должны обрабатываться ConversationHandler
    elif data.startswith(("time_", "dir_", "confirm_", "back_to_time", "back_to_direction", "back_to_range")):
        # Эти callback data должны обрабатываться ConversationHandler
        # Если мы дошли сюда, значит ConversationHandler не в правильном состоянии
        await safe_answer_callback(query, "⚠️ Состояние диалога было сброшено. Пожалуйста, начните заново.")
        
        # Возвращаем пользователя в главное меню
        text = (
            "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
            "🛣️ **Направления:** Минск ⇄ Островец\n\n"
            "💡 **Выберите действие:**"
        )
        
        await safe_edit_message(
                query,
            text,
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    else:
        await safe_answer_callback(query, "❓ Неизвестная команда")

# ==================== ACCOUNT BETA FUNCTIONS ====================

async def handle_account_beta_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню аккаунта (бета версия)"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not bot_auth_manager.is_authenticated(user_id):
        await safe_edit_message(
                query,
            "🔒 **Аккаунт недоступен**\n\n"
            "Для доступа к функциям аккаунта необходимо войти в систему.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔒 Войти в аккаунт", callback_data="login_requests")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile_requests")],
        [InlineKeyboardButton("🎫 Мои бронирования", callback_data="tickets_requests")],
        [InlineKeyboardButton("🤖 Автобронирование", callback_data="auto_booking")],
        [InlineKeyboardButton("🚪 Выйти из аккаунта", callback_data="logout_requests")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
    ]
    
    await safe_edit_message(
                query,
        "👤 **Аккаунт (бета)**\n\n"
        "🔐 **Вы авторизованы в системе**\n\n"
        "💡 **Доступные функции:**\n"
        "• Просмотр профиля\n"
        "• Управление бронированиями\n"
        "• Настройка автобронирования\n\n"
        "⚡ **Выберите действие:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ==================== AUTO BOOKING FUNCTIONS ====================

async def handle_auto_booking_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню автобронирования"""
    query = update.callback_query
    user_id = query.from_user.id
    # Предпочитаем новую систему авторизации (bot_auth_manager). Если пользователь не авторизован там,
    # пробуем legacy user_sessions (RequestsAuthManager). Иначе просим авторизоваться.
    legacy_ok = user_id in user_sessions
    if not bot_auth_manager.is_authenticated(user_id) and not legacy_ok:
        await safe_edit_message(
                query,
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
    
    await safe_edit_message(
                query,
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
        await safe_answer_callback(query, "❌ Необходима авторизация")
        return
    
    await safe_answer_callback(query, "📋 Загружаю ваши бронирования...")
    
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
        
        await safe_edit_message(
                query,
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения бронирований: {e}")
        await safe_edit_message(
                query,
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
        await safe_answer_callback(query, "❌ У вас нет прав администратора")
        return
    
    await safe_edit_message(
                query,
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
        await safe_answer_callback(query, "❌ У вас нет прав администратора")
        return
    
    if action == "admin_monitoring_stats":
        # Статистика мониторингов
        stats_text = admin_panel.get_monitoring_statistics(active_monitors, user_sessions)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_monitoring_stats")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        await safe_edit_message(
                query,
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
        
        await safe_edit_message(
                query,
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
        
        await safe_edit_message(
                query,
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
        
        await safe_edit_message(
                query,
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "admin_emergency":
        # Экстренные функции
        await safe_edit_message(
                query,
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
        
        await safe_edit_message(
                query,
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
        
        await safe_edit_message(
                query,
            result,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "admin_export_data":
        # Экспорт данных
        await safe_answer_callback(query, "📤 Экспортирую данные...")
        
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
        
        await safe_edit_message(
                query,
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
        await safe_edit_message(
                query,
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
    
    await safe_edit_message(
                query,
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
        await safe_edit_message(
                query,
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
            
            await safe_edit_message(
                query,
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
                
                await safe_edit_message(
                query,
                    f"🛣️ **ДОСТУПНЫЕ МАРШРУТЫ**\n\n"
                    f"👥 Пассажиров: {passenger_count}\n"
                    f"📋 Найдено маршрутов: {len(routes)}\n\n"
                    f"💡 Выберите маршрут для бронирования:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
                return CONFIRM_BOOKING
            else:
                await safe_edit_message(
                query,
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
            await safe_edit_message(
                query,
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
        await safe_edit_message(
                query,
            "❌ Бронирование отменено",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
            ]])
        )
        return ConversationHandler.END
    
    if query.data.startswith("route_"):
        route_id = query.data.replace("route_", "")
        passenger_count = context.user_data.get('passenger_count', 1)
        
        await safe_answer_callback(query, "🎫 Бронирую маршрут...")
        
        await safe_edit_message(
                query,
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
            
            await safe_edit_message(
                query,
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Критическая ошибка бронирования: {e}")
            await safe_edit_message(
                query,
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
            CallbackQueryHandler(cancel_conversation, pattern="^back_to_main$"),
            CommandHandler('start', start),
        ],
        per_message=True,
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
            CallbackQueryHandler(cancel_conversation, pattern="^back_to_main$"),
            CommandHandler('start', start),
        ],
        per_message=True,
    )

    # Настройка ConversationHandler для бронирования билетов
    booking_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(book_ticket_handler, pattern="^book_ticket$"),
        ],
        states={
            BOOKING_FROM: [
                CallbackQueryHandler(handle_booking_date_choice, pattern="^date_.*")
            ],
            BOOKING_PASSENGER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_booking_passenger_name)
            ],
            BOOKING_PASSENGER_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_booking_passenger_phone)
            ],
            BOOKING_CONFIRM: [
                CallbackQueryHandler(confirm_booking, pattern="^booking_confirm$")
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^back_to_main$"),
            CommandHandler('start', start),
            CallbackQueryHandler(cancel_conversation, pattern="^booking_cancel$"),
        ],
        per_message=True,
    )

    # Старый обработчик бронирования (переименовываем)
    old_booking_conv_handler = ConversationHandler(
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
            CallbackQueryHandler(cancel_conversation, pattern="^back_to_main$"),
            CommandHandler('start', start),
            CallbackQueryHandler(cancel_conversation, pattern="^cancel_booking$"),
        ],
        per_message=True,
    )

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("monitoring", monitoring_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("recovery_history", recovery_history_command))
    application.add_handler(CommandHandler("system_health", system_health_command))
    application.add_handler(CommandHandler("reset", emergency_reset_command))  # Экстренный сброс
    
    # Добавляем ConversationHandlers
    application.add_handler(monitoring_conv_handler)
    application.add_handler(login_requests_conv_handler)
    application.add_handler(booking_conv_handler)
    application.add_handler(old_booking_conv_handler)
    
    # Добавляем обработчики кнопок (порядок важен!)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)

def main():
    """Главная функция запуска бота"""
    global application, admin_panel, bot_start_time
    
    # Записываем время запуска
    bot_start_time = datetime.now()
    
    # Загружаем существующие мониторинги
    try:
        load_active_monitors()
        safe_log_system("Мониторинги загружены", {"count": len(active_monitors)})
    except Exception as e:
        safe_log_system("Ошибка загрузки мониторингов", {"error": str(e)}, level="error")
    
    # Инициализируем систему обработки крашей в самом начале
    try:
        crash_handler.setup_crash_handling()
        safe_log_system("Система обработки крашей активирована", {"status": "enabled"})
    except Exception as e:
        safe_log_system("Ошибка активации crash handler", {"error": str(e)}, level="error")
    
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        safe_log_bot("Токен бота не найден", {"error": "TELEGRAM_BOT_TOKEN missing"}, level="error")
        return
    
    # Инициализируем админ-панель
    admin_telegram_id = os.getenv('ADMIN_TELEGRAM_ID')
    if admin_telegram_id:
        try:
            admin_panel = AdminPanel(int(admin_telegram_id))
            safe_log_admin("Админ-панель активирована", {"admin_id": admin_telegram_id})
        except ValueError:
            safe_log_admin("Неверный ADMIN_TELEGRAM_ID", {"error": "must_be_number"}, level="error")
    else:
        safe_log_admin("ADMIN_TELEGRAM_ID не установлен", {"warning": "admin_panel_disabled"}, level="warning")
    
    safe_log_bot("Запуск бота MarhrutochkaTG", {
        "python_version": sys.version.split()[0],
        "working_directory": os.getcwd(),
        "process_id": os.getpid(),
        "environment": "railway" if os.getenv('RAILWAY_SERVICE_NAME') else "local"
    })
    
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
        
        # Добавляем фоновую задачу для очистки застрявших callbacks
        job_queue.run_repeating(
            cleanup_stuck_callbacks,
            interval=30,  # Проверка каждые 30 секунд
            first=10,     # Первый запуск через 10 секунд
            name="cleanup_stuck_callbacks"
        )
        
        safe_log_bot("Данные восстановлены", {
            "monitors_count": len(active_monitors),
            "sessions_count": len(user_sessions),
            "callback_cleanup": "enabled"
        })
        
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
                safe_log_bot("Мониторинг восстановлен", {"user_id": user_id})
            except Exception as e:
                safe_log_bot("Ошибка восстановления мониторинга", {
                    "user_id": user_id,
                    "error": str(e)
                }, level="error")
        
        # Запускаем бота (планировщик запустится автоматически)
        safe_log_bot("Бот запущен успешно", {"status": "running"})
        application.run_polling(drop_pending_updates=True)
        
    except Conflict:
        safe_log_bot("Конфликт: бот уже запущен", {"error": "conflict"}, level="error")
    except Exception as e:
        safe_log_bot("Критическая ошибка", {"error": str(e)}, level="error")
        
        # Обрабатываем краш через нашу систему
        try:
            async def handle_crash():
                crash_analysis = await diagnostic_system.analyze_crash_report_from_exception(e)
                if crash_analysis:
                    recovery_result = await auto_recovery.attempt_auto_recovery(crash_analysis)
                    safe_log_system("Автоматическое восстановление завершено", {
                        "success": recovery_result.get("success", False),
                        "actions_count": len(recovery_result.get("actions_taken", [])),
                        "crash_id": crash_analysis.get("crash_id")
                    })
            
            # Запускаем асинхронную обработку краша
            asyncio.run(handle_crash())
            
        except Exception as recovery_error:
            safe_log_system("Ошибка автоматического восстановления", {"error": str(recovery_error)}, level="error")
        
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