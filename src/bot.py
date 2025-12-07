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
import httpx
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PicklePersistence,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.warnings import PTBUserWarning

# Импортируем модули с новой структурой
try:
    from .utils import FinalMarshrutochkaParser
    from .monitoring import setup_logging, railway_logger, crash_handler, diagnostic_system, auto_recovery
    from .admin_panel import AdminPanel
    from .security import security
    from .utils.keyboards import keyboard_factory
    from .utils.telegram_safe import TelegramSafeAPI, safe_edit_message, safe_answer_callback
    from .managers.user_manager import user_manager
    from .storage import create_storage_from_env
except ImportError:
    from utils import FinalMarshrutochkaParser
    from monitoring import setup_logging, railway_logger, crash_handler, diagnostic_system, auto_recovery
    from admin_panel import AdminPanel
    from security import security
    from utils.keyboards import keyboard_factory
    from utils.telegram_safe import TelegramSafeAPI, safe_edit_message, safe_answer_callback
    from managers.user_manager import user_manager
    from storage import create_storage_from_env

# Настройка логирования - используем Railway enhanced logger если доступен
if railway_logger:
    logger = railway_logger
else:
    logger = setup_logging(logging.INFO)

def safe_log(message: str, log_type: str = "system", data: dict = None, level: str = "info"):
    """Универсальная функция безопасного логирования
    
    Args:
        message: Сообщение для логирования
        log_type: Тип лога ("system", "bot", "admin")  
        data: Дополнительные данные
        level: Уровень логирования
    """
    emojis = {"system": "⚙️", "bot": "🤖", "admin": "👨‍💻"}
    method_name = f"{log_type}_action"
    
    if hasattr(logger, method_name):
        getattr(logger, method_name)(message, data or {}, level=level)
    else:
        emoji = emojis.get(log_type, "ℹ️")
        getattr(logger, level, logger.info)(f"{emoji} {message}")

# Обратная совместимость
def safe_log_system(message: str, data: dict = None, level: str = "info"):
    safe_log(message, "system", data, level)

def safe_log_bot(message: str, data: dict = None, level: str = "info"):
    safe_log(message, "bot", data, level)

def safe_log_admin(message: str, data: dict = None, level: str = "info"):
    safe_log(message, "admin", data, level)

# Глобальный мониторинг состояний callback queries
active_callbacks = {}  # {user_id: {'query_id': str, 'start_time': datetime, 'handler': str}}
callback_timeout_seconds = 45  # Таймаут для застрявших callbacks
CLEANUP_JOB_NAME = "cleanup_stuck_callbacks"
RESTART_JOB_NAME = "admin_restart_bot"

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

async def cleanup_stuck_callbacks(context: ContextTypes.DEFAULT_TYPE = None):
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

        # Очищаем пользовательские данные и мониторинги через менеджер
        user_manager.emergency_reset_user(user_id)

        # Очищаем callback tracking
        active_callbacks.pop(user_id, None)

        logger.warning(f"🚨 [{user_id}] Экстренный сброс состояния conversation")
        
    except Exception as e:
        logger.error(f"❌ [{user_id}] Ошибка при экстренном сбросе: {e}")


async def restart_monitoring_scheduler() -> Dict[str, Any]:
    """Перезапустить планировщик мониторингов и восстановить задания."""
    if not job_queue:
        safe_log_system("Попытка перезапуска планировщика без job_queue", level="warning")
        return {
            "success": False,
            "reason": "job_queue_unavailable"
        }
    
    removed_jobs = 0
    failures: List[Dict[str, Any]] = []
    
    try:
        for job in list(job_queue.jobs()):
            job.schedule_removal()
            removed_jobs += 1
    except Exception as removal_error:
        safe_log_system("Ошибка очистки job queue перед перезапуском", {
            "error": str(removal_error)
        }, level="error")
        logger.error("Ошибка при очистке job queue", exc_info=True)
        return {
            "success": False,
            "reason": "job_cleanup_failed",
            "error": str(removal_error)
        }
    
    # Даём планировщику возможность применить удаления
    await asyncio.sleep(0)
    
    # Восстанавливаем системные задачи
    job_queue.run_repeating(
        cleanup_stuck_callbacks,
        interval=30,
        first=10,
        name=CLEANUP_JOB_NAME
    )
    
    restored_monitors = 0
    for user_id in list(active_monitors.keys()):
        try:
            job_queue.run_repeating(
                check_routes_for_user,
                interval=300,
                first=10,
                name=f"monitor_{user_id}",
                data=user_id
            )
            restored_monitors += 1
        except Exception as monitor_error:
            failure_info = {
                "user_id": user_id,
                "error": str(monitor_error)
            }
            failures.append(failure_info)
            safe_log_bot("Ошибка восстановления мониторинга при перезапуске планировщика", failure_info, level="error")
    
    safe_log_system("Планировщик мониторингов перезапущен", {
        "jobs_removed": removed_jobs,
        "monitors_restored": restored_monitors,
        "failures": len(failures)
    })
    
    return {
        "success": len(failures) == 0,
        "jobs_removed": removed_jobs,
        "monitors_restored": restored_monitors,
        "failures": failures
    }


async def trigger_bot_restart(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает приложение для последующего перезапуска."""
    restart_info = context.application.bot_data.setdefault("restart_info", {})
    restart_info.setdefault("pending", True)
    restart_info["triggered_at"] = datetime.now().isoformat()
    safe_log_system("Перезапуск бота инициирован", restart_info)
    context.application.stop_running()


# Игнорируем предупреждения от python-telegram-bot о per_message
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=PTBUserWarning)

# Отключаем подробные сообщения от httpx, используемого библиотекой telegram
logging.getLogger("httpx").setLevel(logging.WARNING)

# Состояния для ConversationHandler
(CHOOSE_DATE, CHOOSE_DIRECTION, CHOOSE_TIME_TYPE, CHOOSE_TIME_RANGE,
 CONFIRM_MONITORING, SEARCH_DATE) = range(6)

# Глобальные переменные
parser = None
job_queue = None  # Встроенная очередь заданий PTB
active_monitors = user_manager.active_monitors  # user_id -> monitor_config
user_data_store = user_manager.user_data_store  # user_id -> user_data
application = None  # will hold the Application instance
admin_panel = None  # Административная панель

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

# Создаем директорию для данных (используется persistence)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

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

# ==================== UTILITY FUNCTIONS ====================

def create_webapp_url(direction: Optional[str] = None, date: str = None) -> str:
    """Создает URL для веб-приложения маршруточки с предвыбранным направлением"""
    base_url = "https://билет.маршруточка.бел/"
    
    # Если есть направление или дата, добавляем их как hash-параметры
    # Сайт может их прочитать через window.location.hash в JavaScript
    params = []
    
    if direction and direction not in ["general", "both", "all"]:
        # Преобразуем направление в формат from-to
        direction_map = {
            "minsk_ostrovets": "from=minsk&to=ostrovets",
            "ostrovets_minsk": "from=ostrovets&to=minsk",
            "minsk_smorgon": "from=minsk&to=smorgon",
            "smorgon_minsk": "from=smorgon&to=minsk",
            "ostrovets_smorgon": "from=ostrovets&to=smorgon",
            "smorgon_ostrovets": "from=smorgon&to=ostrovets"
        }
        
        if direction in direction_map:
            params.append(direction_map[direction])
            
            # Добавляем дату только если есть направление
            if date:
                params.append(f"date={date}")
    
    # Формируем URL с параметрами в hash
    if params:
        return f"{base_url}#{'&'.join(params)}"
    
    return base_url

def create_webapp_keyboard(direction: str = None, date: str = None, additional_buttons: list = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками веб-приложений"""
    keyboard = []
    
    # Создаем URL с параметрами
    webapp_url = create_webapp_url(direction, date)
    
    # Выбираем текст кнопки в зависимости от наличия параметров
    if direction and direction not in ["general", "both", "all"]:
        button_text = "🌐 Открыть сайт бронирования"
        
        # Добавляем кнопку с параметрами
        keyboard.append([
            InlineKeyboardButton(button_text, web_app=WebAppInfo(url=webapp_url))
        ])
        
        # Добавляем специальную информацию для маршрутов через Сморгонь
        if "smorgon" in direction:
            keyboard.append([
                InlineKeyboardButton("ℹ️ Информация о Сморгони", callback_data="smorgon_info")
            ])
    else:
        # Кнопка для общего доступа к сайту
        keyboard.append([
            InlineKeyboardButton("🚌 Открыть сайт маршруточки", web_app=WebAppInfo(url=webapp_url))
        ])
    
    # Добавляем дополнительные кнопки если есть
    if additional_buttons:
        keyboard.extend(additional_buttons)
    
    return InlineKeyboardMarkup(keyboard)

def get_date_keyboard():
    """Клавиатура для выбора даты"""
    return keyboard_factory.get_date_keyboard()

def get_direction_keyboard():
    """Клавиатура для выбора направления"""
    return keyboard_factory.get_direction_keyboard()

def get_time_type_keyboard():
    """Клавиатура для выбора типа времени"""
    return keyboard_factory.get_time_type_keyboard()

def get_time_range_keyboard(time_type):
    """Клавиатура для выбора диапазона времени"""
    return keyboard_factory.get_time_range_keyboard(time_type)

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
    """Возвращает клавиатуру главного меню."""
    is_admin = admin_panel and admin_panel.is_admin(user_id)
    return keyboard_factory.get_main_menu_keyboard(user_id, is_admin)

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

async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /reload - Перезагрузка бота на Railway"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    admin_id = os.getenv('ADMIN_TELEGRAM_ID')
    if not admin_id or str(user_id) != admin_id:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды.",
            parse_mode='Markdown'
        )
        return
    
    # Получаем переменные Railway
    railway_token = os.getenv('RAILWAY_TOKEN')
    railway_service_id = os.getenv('RAILWAY_SERVICE_ID')
    
    if not railway_token or not railway_service_id:
        await update.message.reply_text(
            "❌ **Ошибка конфигурации**\n\n"
            "Не найдены переменные окружения:\n"
            f"• RAILWAY_TOKEN: {'✅' if railway_token else '❌'}\n"
            f"• RAILWAY_SERVICE_ID: {'✅' if railway_service_id else '❌'}\n\n"
            "💡 Добавьте их в настройках Railway.",
            parse_mode='Markdown'
        )
        return
    
    # Отправляем уведомление о начале перезагрузки
    status_msg = await update.message.reply_text(
        "🔄 **Перезагрузка бота...**\n\n"
        "⏳ Отправка запроса на Railway API...",
        parse_mode='Markdown'
    )
    
    try:
        # Railway GraphQL API endpoint
        url = "https://backboard.railway.app/graphql/v2"
        
        # GraphQL mutation для перезапуска сервиса
        query = """
        mutation serviceInstanceRedeploy($serviceId: String!) {
            serviceInstanceRedeploy(serviceId: $serviceId)
        }
        """
        
        headers = {
            "Authorization": f"Bearer {railway_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "variables": {
                "serviceId": railway_service_id
            }
        }
        
        # Отправляем запрос
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                
                if "errors" in result:
                    error_msg = result["errors"][0].get("message", "Unknown error")
                    await status_msg.edit_text(
                        f"❌ **Ошибка Railway API**\n\n"
                        f"```\n{error_msg}\n```",
                        parse_mode='Markdown'
                    )
                    safe_log_admin("Ошибка перезагрузки Railway", {"error": error_msg}, level="error")
                else:
                    await status_msg.edit_text(
                        "✅ **Перезагрузка запущена**\n\n"
                        "🔄 Бот будет перезапущен через несколько секунд.\n"
                        "⏰ Обычно это занимает 30-60 секунд.\n\n"
                        "💡 Используйте /status чтобы проверить состояние.",
                        parse_mode='Markdown'
                    )
                    safe_log_admin("Перезагрузка бота на Railway инициирована", {
                        "user_id": user_id,
                        "service_id": railway_service_id
                    })
            else:
                await status_msg.edit_text(
                    f"❌ **Ошибка HTTP {response.status_code}**\n\n"
                    f"```\n{response.text[:500]}\n```",
                    parse_mode='Markdown'
                )
                safe_log_admin("Ошибка HTTP при перезагрузке Railway", {
                    "status_code": response.status_code,
                    "response": response.text[:500]
                }, level="error")
                
    except httpx.TimeoutException:
        await status_msg.edit_text(
            "⏱️ **Таймаут запроса**\n\n"
            "Не удалось связаться с Railway API.\n"
            "Попробуйте позже.",
            parse_mode='Markdown'
        )
        safe_log_admin("Таймаут при перезагрузке Railway", level="error")
    except Exception as e:
        await status_msg.edit_text(
            f"❌ **Неожиданная ошибка**\n\n"
            f"```\n{str(e)[:500]}\n```",
            parse_mode='Markdown'
        )
        safe_log_admin("Исключение при перезагрузке Railway", {"error": str(e)}, level="error")

@callback_handler_protection(timeout=30)
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню - универсальный для всех conversation"""
    query = update.callback_query
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
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
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
    
    if user_manager.remove_user_monitor(user_id):
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
                (
                    f"🔍 **Поиск маршрутов...**\n\n"
                    f"📍 **Маршрут:** {from_city} → {to_city}\n"
                    f"📅 **Дата:** {selected_date}"
                ),
                parse_mode='Markdown'
            )
            
            # Запускаем поиск маршрутов
            await perform_route_search(query, user_id, from_city, to_city, selected_date)
            return ConversationHandler.END
        else:
            # Обычный поток - выбираем направление
            await safe_edit_message(
                query,
                (
                    f"✅ **Выбрана дата:** {selected_date}\n\n"
                    "🛣️ **Шаг 2:** Выберите направление:"
                ),
                reply_markup=get_direction_keyboard(),
                parse_mode='Markdown'
            )
            
            return CHOOSE_DIRECTION
    
    elif data == "custom_date":
        await safe_edit_message(
                query,
            (
                "📅 **Введите дату в формате YYYY-MM-DD**\n\n"
                "Например: `2025-01-15`\n\n"
                "Или нажмите кнопку ниже для возврата:"
            ),
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
            (
                "🚌 **Добро пожаловать в бот мониторинга маршруточки!**\n\n"
                "🛣️ **Направления:** Минск ⇄ Островец\n"
                "🌐 **Источник:** билет.маршруточка.бел\n\n"
                "💡 **Выберите действие:**"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    return CHOOSE_DATE

@callback_handler_protection(timeout=20)
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
        # По умолчанию устанавливаем время отправления
        user_data_store[user_id]['time_type'] = 'departure'
        
        direction_text = {
            "minsk_ostrovets": "Минск → Островец",
            "ostrovets_minsk": "Островец → Минск", 
            "both": "Оба направления"
        }.get(direction, direction)
        
        await safe_edit_message(
                query,
            f"✅ **Направление:** {direction_text}\n\n"
            "🕐 **Шаг 2:** Выберите время отправления:\n\n"
            "💡 Вы можете выбрать время из списка или написать свой диапазон в формате ЧЧ:ММ-ЧЧ:ММ (например, 07:00-09:00)",
            reply_markup=get_time_range_keyboard('departure'),
            parse_mode='Markdown'
        )
        
        return CHOOSE_TIME_RANGE
        
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
    """Обработка выбора типа времени (используется при изменении настроек мониторинга)."""
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
    
    if data == "back_to_time_range" or data == "back_to_range_list":
        # Возвращаемся к выбору диапазона времени
        direction_text = {
            "minsk_ostrovets": "Минск → Островец",
            "ostrovets_minsk": "Островец → Минск"
        }.get(user_data_store[user_id].get('direction', ''), "")
        
        await safe_edit_message(
                query,
            f"✅ **Направление:** {direction_text}\n\n"
            "🕐 **Шаг 2:** Выберите время отправления:\n\n"
            "💡 Вы можете выбрать время из списка или написать свой диапазон в формате ЧЧ:ММ-ЧЧ:ММ (например, 07:00-09:00)",
            reply_markup=get_time_range_keyboard('departure'),
            parse_mode='Markdown'
        )
        return CHOOSE_TIME_RANGE
    
    elif data == "back_to_direction":
        # Возвращаемся к выбору направления
        await safe_edit_message(
                query,
            f"✅ **Дата:** {user_data_store[user_id].get('date', '')}\n\n"
            "🛣️ **Шаг 2:** Выберите направление:",
            reply_markup=get_direction_keyboard(),
            parse_mode='Markdown'
        )
        return CHOOSE_DIRECTION
    
    elif data == "range_custom":
        await safe_edit_message(
            query,
            "🕐 **Введите желаемый диапазон времени**\n\n"
            "Формат: `HH:MM-HH:MM` (например, 07:00-09:00)",
            parse_mode='Markdown'
        )
        return CHOOSE_TIME_RANGE
    
    elif data.startswith("range_"):
        time_range = data.replace("range_", "")
        
        user_data_store[user_id]['time_range'] = time_range
        
        config_text = format_monitor_config(user_data_store[user_id])
        
        await safe_edit_message(
            query,
            f"✅ **Настройки мониторинга:**\n\n{config_text}\n\n"
            "❓ **Все верно?**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, все верно!", callback_data="confirm_yes")],
                [InlineKeyboardButton("🔙 Изменить время", callback_data="back_to_time_range")]
            ]),
            parse_mode='Markdown'
        )
        
        return CONFIRM_MONITORING
async def _ensure_monitoring_session(user_id: int, query, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет, что данные для запуска мониторинга корректны."""
    session = user_data_store.get(user_id)
    if not session:
        await safe_edit_message(
            query,
            "⚠️ **Настройка мониторинга была сброшена**\n\n"
            "Не удалось найти сохраненные данные. Начните настройку заново.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
        return None
    
    required_fields = ["date", "direction", "time_type", "time_range"]
    missing = [field for field in required_fields if field not in session]
    if missing:
        logger.warning(f"Недостаточно данных для запуска мониторинга пользователя {user_id}: отсутствует {missing}")
        await safe_edit_message(
            query,
            "⚠️ **Не хватает данных для запуска мониторинга**\n\n"
            "Пожалуйста, пройдите настройку заново.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
        return None
    
    return session.copy()

async def _store_monitoring_config(user_id: int, query, context: ContextTypes.DEFAULT_TYPE, session: Dict[str, Any]):
    """Сохраняет конфигурацию мониторинга и запускает планировщик при необходимости."""
    monitor_payload = session.copy()
    monitor_payload['chat_id'] = query.message.chat_id
    user_manager.set_user_monitor(user_id, monitor_payload)
    config = user_manager.get_user_monitor(user_id)
    
    if job_queue:
        try:
            job_queue.run_repeating(
                check_routes_for_user,
                interval=300,
                first=10,
                name=f"monitor_{user_id}",
                data=user_id
            )
        except Exception as job_error:
            logger.error(f"Не удалось добавить задачу мониторинга для пользователя {user_id}: {job_error}")
    
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

async def _show_adjust_menu(user_id: int, query):
    """Показывает меню изменения параметров мониторинга."""
    if user_id not in user_data_store:
        await safe_edit_message(
            query,
            "ℹ️ **Сессия настройки недоступна**\n\n"
            "Начните настройку заново, чтобы изменить параметры.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
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
    return CONFIRM_MONITORING

async def _return_to_time_range(user_id: int, query):
    """Возвращает пользователя к выбору диапазона времени."""
    direction_text = {
        "minsk_ostrovets": "Минск → Островец",
        "ostrovets_minsk": "Островец → Минск"
    }.get(user_data_store.get(user_id, {}).get('direction', ''), "")
    
    await safe_edit_message(
        query,
        f"✅ **Направление:** {direction_text}\n\n"
        "🕐 **Шаг 2:** Выберите время отправления:\n\n"
        "💡 Вы можете выбрать время из списка или написать свой диапазон в формате ЧЧ:ММ-ЧЧ:ММ (например, 07:00-09:00)",
        reply_markup=get_time_range_keyboard('departure'),
        parse_mode='Markdown'
    )
    return CHOOSE_TIME_RANGE

@callback_handler_protection(timeout=25)
async def handle_monitoring_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения мониторинга"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "confirm_yes":
        session = await _ensure_monitoring_session(user_id, query, context)
        if not session:
            return ConversationHandler.END

        await _store_monitoring_config(user_id, query, context, session)
        return ConversationHandler.END

    elif data in {"back_to_range", "back_to_time_range"}:
        return await _return_to_time_range(user_id, query)

    return CONFIRM_MONITORING

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода"""
    user_id = update.effective_user.id
    text = security.sanitize_input(update.message.text)
    
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
    normalized_range = security.normalize_time_range(text)
    if normalized_range:
        user_data_store[user_id]['time_range'] = normalized_range
        
        config_text = format_monitor_config(user_data_store[user_id])
        
        await update.message.reply_text(
            f"✅ **Настройки мониторинга:**\n\n{config_text}\n\n"
            "❓ **Все верно?**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, все верно!", callback_data="confirm_yes")],
                [InlineKeyboardButton("🔙 Изменить время", callback_data="back_to_time_range")]
            ]),
            parse_mode='Markdown'
        )
        
        return CONFIRM_MONITORING
    elif (
        normalized_range is None
        and user_id in user_data_store
        and user_data_store[user_id].get('time_type')
        and 'time_range' not in user_data_store[user_id]
    ):
        # Пользователь пытался ввести диапазон, но он некорректный
        await update.message.reply_text(
            "❌ **Неверный формат времени**\n\n"
            "Используйте формат ЧЧ:ММ-ЧЧ:ММ, например:\n"
            "• `07:00-09:00` — утренний диапазон\n"
            "• `22:00-02:00` — через полночь\n\n"
            "Допускаются пробелы вокруг дефиса. Часы должны быть от 00 до 23, минуты от 00 до 59.",
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
                    "• `22:00-02:00`",
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

        def parse_time_to_minutes(time_str: str) -> Optional[int]:
            """Конвертируем HH:MM в минуты от начала суток."""
            try:
                hours, minutes = map(int, time_str.split(":")[:2])
                return hours * 60 + minutes
            except (ValueError, AttributeError, TypeError):
                return None

        def get_duration_text(route: Dict) -> str:
            """Возвращает длительность рейса в формате H:MM."""
            duration_minutes = None

            for key in ("duration_minutes", "calculated_duration_minutes"):
                value = route.get(key)
                if isinstance(value, (int, float)):
                    duration_minutes = int(value)
                    break

            if duration_minutes is None:
                dep_minutes = parse_time_to_minutes(route.get('departure_time'))
                arr_minutes = parse_time_to_minutes(route.get('arrival_time'))
                if dep_minutes is not None and arr_minutes is not None:
                    # Если прибытие раньше отправления - считаем, что рейс приходит на следующий день
                    if arr_minutes < dep_minutes:
                        arr_minutes += 24 * 60
                    duration_minutes = arr_minutes - dep_minutes

            if duration_minutes is None:
                duration_str = route.get('duration')
                if duration_str:
                    hours_match = re.search(r'(\d+)\s*ч', duration_str)
                    minutes_match = re.search(r'(\d+)\s*мин', duration_str)
                    hours = int(hours_match.group(1)) if hours_match else 0
                    minutes = int(minutes_match.group(1)) if minutes_match else 0
                    if hours or minutes:
                        duration_minutes = hours * 60 + minutes
                    else:
                        return duration_str

            if duration_minutes is None:
                return "н/д"

            hours = duration_minutes // 60
            minutes = duration_minutes % 60
            return f"{hours}:{minutes:02d}"

        def format_route_line(route: Dict) -> str:
            seats_raw = route.get('available_seats', 0)
            try:
                seats = int(seats_raw)
            except (ValueError, TypeError):
                seats = 0
            
            if seats <= 0:
                seat_emoji = "🚫"
            elif seats <= 3:
                seat_emoji = "🔥"
            else:
                seat_emoji = "✅"
            duration_text = get_duration_text(route)
            departure = route.get('departure_time', '?')
            return f"🚀 {departure} ({duration_text}) {seat_emoji} {seats}"

        message_parts = [format_route_line(route) for route in routes[:5]]

        if len(routes) > 5:
            message_parts.append(f"... и еще {len(routes) - 5} рейсов")

        message_parts.extend([
            "",
            "🔔 НАЙДЕНЫ ПОДХОДЯЩИЕ РЕЙСЫ!",
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
                        
                        # Специальный формат для маршрутов через Сморгонь (Минск → Островец)
                        if route.get('via_smorgon') and from_city == "Минск" and to_city == "Островец":
                            departure_time = route.get('departure_time')
                            smorgon_arrival = route.get('smorgon_arrival', '')
                            smorgon_departure = route.get('smorgon_departure', '')
                            arrival_time = route.get('arrival_time')
                            duration = route.get('duration', 'н/д')
                            
                            message_parts.append(f"{i}. Минск {departure_time}")
                            if smorgon_arrival and smorgon_departure:
                                # Используем динамически рассчитанное время или стандартное
                                smorgon_duration_minutes = route.get('calculated_smorgon_ostrovets_minutes', 65)
                                smorgon_hours = smorgon_duration_minutes // 60
                                smorgon_mins = smorgon_duration_minutes % 60
                                if smorgon_hours > 0:
                                    smorgon_duration = f"{smorgon_hours} ч {smorgon_mins} мин"
                                else:
                                    smorgon_duration = f"{smorgon_mins} мин"
                                message_parts.append(f"   {smorgon_departure} → {arrival_time} ({smorgon_duration})")
                            else:
                                message_parts.append(f"   → {arrival_time} ({duration})")
                        else:
                            time_info = f"**{route.get('departure_time')} → {route.get('arrival_time')}**"
                            duration = route.get('duration', 'н/д')
                            message_parts.append(f"{i}. {time_info} ({duration})")
                        
                        # Проверяем, нужно ли показывать места
                        is_smorgon_to_ostrovets = (from_city == "Сморгонь" and to_city == "Островец")
                        
                        if not is_smorgon_to_ostrovets and seats is not None:
                            seat_emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
                            message_parts.append(f"   {seat_emoji} {seats} мест")
                        
                        # Добавляем информацию о промежуточных городах только для других маршрутов
                        if not is_smorgon_to_ostrovets:
                            if route.get('via_smorgon') and not (from_city == "Минск" and to_city == "Островец"):
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
                    
                    # Специальный формат для маршрутов через Сморгонь (Минск → Островец)
                    if route.get('via_smorgon') and from_city == "Минск" and to_city == "Островец":
                        departure_time = route.get('departure_time')
                        smorgon_arrival = route.get('smorgon_arrival', '')
                        smorgon_departure = route.get('smorgon_departure', '')
                        arrival_time = route.get('arrival_time')
                        duration = route.get('duration', 'н/д')
                        
                        message_parts.append(f"{i}. Минск {departure_time}")
                        if smorgon_arrival and smorgon_departure:
                            # Используем динамически рассчитанное время или стандартное
                            smorgon_duration_minutes = route.get('calculated_smorgon_ostrovets_minutes', 65)
                            smorgon_hours = smorgon_duration_minutes // 60
                            smorgon_mins = smorgon_duration_minutes % 60
                            if smorgon_hours > 0:
                                smorgon_duration = f"{smorgon_hours} ч {smorgon_mins} мин"
                            else:
                                smorgon_duration = f"{smorgon_mins} мин"
                            message_parts.append(f"   {smorgon_departure} → {arrival_time} ({smorgon_duration})")
                        else:
                            message_parts.append(f"   → {arrival_time} ({duration})")
                    else:
                        time_info = f"**{route.get('departure_time')} → {route.get('arrival_time')}**"
                        duration = route.get('duration', 'н/д')
                        message_parts.append(f"{i}. {time_info} ({duration})")
                    
                    # Проверяем, нужно ли показывать места
                    is_smorgon_to_ostrovets = (from_city == "Сморгонь" and to_city == "Островец")
                    
                    if not is_smorgon_to_ostrovets and seats is not None:
                        seat_emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
                        message_parts.append(f"   {seat_emoji} {seats} мест")
                    
                    # Добавляем информацию о промежуточных городах только для других маршрутов
                    if not is_smorgon_to_ostrovets:
                        if route.get('via_smorgon') and not (from_city == "Минск" and to_city == "Островец"):
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
    user_id = update.effective_user.id
    admin_id = os.getenv('ADMIN_TELEGRAM_ID')
    is_admin = admin_id and str(user_id) == admin_id
    
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
• `/help` - эта справка
• `/status` - статус системы"""
    
    if is_admin:
        help_text += """

👨‍💻 **Команды администратора:**
• `/reload` - перезагрузка бота на Railway
• `/recovery_history` - история восстановлений
• `/system_health` - проверка здоровья системы
• `/reset` - экстренный сброс"""
    
    help_text += """

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
        try:
            await context.bot.get_me()
            network_ok = True
        except Exception:
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
        [InlineKeyboardButton("🏙️ Минск → Островец", callback_data="search_dir_minsk_ostrovets")],
        [InlineKeyboardButton("🏘️ Островец → Минск", callback_data="search_dir_ostrovets_minsk")],
        [InlineKeyboardButton("🎯 Выбрать города по отдельности", callback_data="search_by_cities")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    if update.message:
        await update.message.reply_text(
            "🔍 **Выберите маршрут для поиска:**\n\n"
            "🏙️🏘️ **Популярные направления** - быстрый доступ к самым популярным маршрутам\n"
            "🎯 **По отдельности** - выберите откуда и куда, включая Сморгонь",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        query = update.callback_query
        await safe_edit_message(
                query,
            "🔍 **Выберите маршрут для поиска:**\n\n"
            "🏙️🏘️ **Популярные направления** - быстрый доступ к самым популярным маршрутам\n"
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
            
            # Проверяем, является ли это маршрутом через Сморгонь
            from_city = route.get('from_city', '')
            to_city = route.get('to_city', '')
            
            # Специальный формат для маршрутов через Сморгонь (Минск → Островец)
            if route.get('via_smorgon') and from_city == "Минск" and to_city == "Островец":
                departure_time = route.get('departure_time')
                smorgon_arrival = route.get('smorgon_arrival', '')
                smorgon_departure = route.get('smorgon_departure', '')
                arrival_time = route.get('arrival_time')
                duration = route.get('duration', 'н/д')
                
                section.append(f"{i}. Минск {departure_time}")
                if smorgon_arrival and smorgon_departure:
                    # Используем динамически рассчитанное время или стандартное
                    smorgon_duration_minutes = route.get('calculated_smorgon_ostrovets_minutes', 65)
                    smorgon_hours = smorgon_duration_minutes // 60
                    smorgon_mins = smorgon_duration_minutes % 60
                    if smorgon_hours > 0:
                        smorgon_duration = f"{smorgon_hours} ч {smorgon_mins} мин"
                    else:
                        smorgon_duration = f"{smorgon_mins} мин"
                    section.append(f"   {smorgon_departure} → {arrival_time} ({smorgon_duration})")
                else:
                    section.append(f"   → {arrival_time} ({duration})")
            else:
                # Обычный формат
                time_info = f"**{route.get('departure_time')} → {route.get('arrival_time')}**"
                duration = route.get('duration', 'н/д')
                section.append(f"{i}. {time_info} ({duration})")
            
            # Проверяем, нужно ли показывать места (для Сморгонь-Островец не показываем)
            is_smorgon_to_ostrovets = (from_city == "Сморгонь" and to_city == "Островец")
            
            if not is_smorgon_to_ostrovets and seats is not None:
                seat_emoji = "🚫" if seats == 0 else "🔥" if seats <= 3 else "✅"
                section.append(f"   {seat_emoji} {seats} мест")
            
            # Добавляем информацию о промежуточных городах только для других маршрутов
            if not is_smorgon_to_ostrovets:
                if route.get('via_smorgon') and not (from_city == "Минск" and to_city == "Островец"):
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

# ==================== УДАЛЕНЫ ФУНКЦИИ АВТОБРОНИРОВАНИЯ ====================
# Все функции бронирования были удалены для упрощения архитектуры
# Бот теперь фокусируется только на поиске и мониторинге маршрутов

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
    
    elif data == "confirm_yes":
        session = await _ensure_monitoring_session(user_id, query, context)
        if session:
            await _store_monitoring_config(user_id, query, context, session)
        return ConversationHandler.END
    
    elif data == "confirm_no":
        return await _show_adjust_menu(user_id, query)
    
    elif data in {"back_to_range", "back_to_time_range"}:
        return await _return_to_time_range(user_id, query)
    
    elif data == "stop_monitoring":
        return await stop_monitoring(update, context)
    
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
    
    # Удален обработчик бронирования - функция больше не поддерживается
    
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
    
    elif data == "book_ticket":
        # Бронирование удалено - показываем главное меню
        await safe_edit_message(query,
            "🏠 **Главное меню**\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    elif data == "booking_confirm":
        # Бронирование удалено - показываем главное меню
        await safe_edit_message(query,
            "🏠 **Главное меню**\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
        
    elif data == "booking_cancel":
        # Переходим в главное меню
        text = "🏠 **Главное меню**\n\nВыберите действие:"
        await safe_edit_message(query, text, reply_markup=get_main_menu_keyboard(user_id))
    
    elif data.startswith("bookings_"):
        # Функции бронирования удалены - переходим в главное меню
        await safe_edit_message(query,
            "🏠 **Главное меню**\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    elif data == "my_monitors":
        await my_monitors(update, context)
    
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
        # Автобронирование удалено - показываем главное меню
        await safe_edit_message(query,
            "🏠 **Главное меню**\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    elif data == "admin_panel":
        # Админ-панель
        await handle_admin_panel(update, context)
    
    # Обработчики админ-панели
    elif data.startswith("admin_"):
        await handle_admin_functions(update, context, data)
    
    # Обработчики автобронирования
    elif data == "my_bookings":
        # Бронирования удалены - показываем главное меню
        await safe_edit_message(query,
            "🏠 **Главное меню**\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    
    elif data == "auto_book_monitoring":
        # Автобронирование удалено - показываем главное меню
        await safe_edit_message(query,
            "🏠 **Главное меню**\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard(user_id),
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
        # Аккаунт недоступен
        await safe_edit_message(
                query,
            "🔒 **Аккаунт недоступен**\n\n"
            "Функции аккаунта были удалены.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
    
    # Обработка кнопок изменения настроек мониторинга
    elif data == "change_date":
        await safe_edit_message(
            query,
            "📅 **Изменение даты**\n\n"
            "Выберите новую дату поездки:",
            reply_markup=get_date_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "change_direction":
        await safe_edit_message(
            query,
            "🛣️ **Изменение направления**\n\n"
            "Выберите новое направление:",
            reply_markup=get_direction_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "change_time":
        await safe_edit_message(
            query,
            "⏰ **Изменение времени**\n\n"
            "Что важнее для вас?",
            reply_markup=get_time_type_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "back_to_time_type":
        await safe_edit_message(
            query,
            "⏰ **Выбор времени**\n\n"
            "Что важнее для вас?",
            reply_markup=get_time_type_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "cancel_setup":
        # Очищаем данные пользователя
        if user_id in user_data_store:
            del user_data_store[user_id]
        context.user_data.clear()
        
        # Возвращаем в главное меню
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
    
    # Проверяем callback data, которые должны обрабатываться ConversationHandler
    elif data.startswith(("time_", "dir_", "confirm_", "back_to_direction", "back_to_range")):
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
        stats_text = admin_panel.get_monitoring_statistics(active_monitors)
        
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
        users_text = admin_panel.get_active_users_info(active_monitors, user_data_store)
        
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
    
    elif action == "admin_restart_bot":
        # Подтверждение перезапуска бота
        await safe_edit_message(
                query,
            "🔁 **ПЕРЕЗАГРУЗКА БОТА**\n\n"
            "⚠️ После подтверждения бот будет остановлен и автоматически запущен заново.\n"
            "Активные мониторинги восстановятся после перезапуска.",
            reply_markup=admin_panel.get_restart_confirmation_keyboard(),
            parse_mode='Markdown'
        )
    
    elif action == "admin_restart_bot_confirm":
        # Планирование перезапуска бота
        keyboard = [
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        delay_seconds = 3
        restart_info = context.application.bot_data.get("restart_info", {})
        pending = restart_info.get("pending", False)
        
        if pending:
            requested_at_iso = restart_info.get("requested_at")
            scheduled_for_iso = restart_info.get("scheduled_for")
            requested_at = datetime.fromisoformat(requested_at_iso).strftime('%d.%m.%Y %H:%M:%S') if requested_at_iso else "неизвестно"
            scheduled_time = datetime.fromisoformat(scheduled_for_iso).strftime('%d.%m.%Y %H:%M:%S') if scheduled_for_iso else "неизвестно"
            
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
                "delay_seconds": delay_seconds
            }
            
            if context.application.job_queue:
                for existing_job in context.application.job_queue.get_jobs_by_name(RESTART_JOB_NAME):
                    existing_job.schedule_removal()
                context.application.job_queue.run_once(
                    trigger_bot_restart,
                    when=delay_seconds,
                    name=RESTART_JOB_NAME
                )
            
            message_text = (
                "🔁 **ПЕРЕЗАГРУЗКА БОТА**\n\n"
                "✅ Перезапуск запланирован.\n"
                f"🕒 Запрос: {requested_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
                f"🚀 Ожидаемое время перезапуска: {scheduled_for.strftime('%d.%m.%Y %H:%M:%S')}\n"
                f"⏳ Задержка: {delay_seconds} сек.\n\n"
                "Бот автоматически завершит работу и перезапустится."
            )
        
        await safe_edit_message(
                query,
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "admin_restart_scheduler":
        # Перезапуск планировщика мониторингов
        scheduler_result = await restart_monitoring_scheduler()
        keyboard = [
            [InlineKeyboardButton("🔙 Экстренные функции", callback_data="admin_emergency")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        
        jobs_removed = scheduler_result.get("jobs_removed", 0)
        restored_monitors = scheduler_result.get("monitors_restored", 0)
        failures = scheduler_result.get("failures", [])
        
        if scheduler_result.get("success"):
            message_text = (
                "🔄 **ПЕРЕЗАПУСК ПЛАНИРОВЩИКА**\n\n"
                "✅ Планировщик мониторингов перезапущен.\n"
                f"🗑️ Удалено задач: {jobs_removed}\n"
                f"🔔 Восстановлено мониторингов: {restored_monitors}\n"
                "🧹 Системная задача очистки callback'ов активирована."
            )
        else:
            reason = scheduler_result.get("reason", "unknown")
            message_text = (
                "❌ **ОШИБКА ПЕРЕЗАПУСКА ПЛАНИРОВЩИКА**\n\n"
                f"Причина: `{reason}`"
            )
        
        if failures:
            message_text += "\n\n⚠️ Не удалось восстановить мониторинги:\n"
            for failure in failures[:5]:
                message_text += f"• User ID {failure.get('user_id')}: {failure.get('error')}\n"
            if len(failures) > 5:
                message_text += f"… и ещё {len(failures) - 5} пользователей\n"
        
        await safe_edit_message(
                query,
            message_text,
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
        result = admin_panel.clear_user_cache(user_data_store)
        
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
        
        export_result = admin_panel.export_data(active_monitors)
        
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

    # ConversationHandler для бронирования удален - бронирование больше не поддерживается

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("monitoring", monitoring_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("recovery_history", recovery_history_command))
    application.add_handler(CommandHandler("system_health", system_health_command))
    application.add_handler(CommandHandler("reset", emergency_reset_command))  # Экстренный сброс
    application.add_handler(CommandHandler("reload", reload_command))  # Перезагрузка бота на Railway
    
    # Добавляем ConversationHandlers
    application.add_handler(monitoring_conv_handler)
    # booking_conv_handler удален - бронирование не поддерживается
    
    # Добавляем обработчики кнопок (порядок важен!)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)

def main():
    """Главная функция запуска бота"""
    global application, admin_panel, active_monitors, user_data_store

    safe_log_system("Мониторинги работают в memory-only режиме", {})

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

    # Создаем приложение с постоянным локальным хранилищем состояния (для user_data/chat_data/bot_data)
    persistence_path = os.path.join(DATA_DIR, 'bot_state.pickle')
    persistence = PicklePersistence(filepath=persistence_path)
    application = Application.builder().token(token).persistence(persistence).build()

    try:
        # Регистрируем обработчики
        register_handlers(application)

        # Получаем job_queue
        global job_queue
        job_queue = application.job_queue

        # Настраиваем устойчивое хранилище мониторингов (Redis или файл)
        try:
            storage = create_storage_from_env()
            user_manager.set_storage(storage)
        except Exception as e:
            storage = None
            safe_log_system("Не удалось инициализировать персистентное storage", {"error": str(e)}, level="error")

        # Привязываем persistence-хранилища Telegram к менеджеру пользователей
        # user_data/chat_data/bot_data остаются в PicklePersistence
        # active_monitors синхронизируем со storage
        loaded = 0
        if storage:
            loaded = user_manager.load_monitors_from_storage()

        # Создаем/обновляем структуры в bot_data и биндим на менеджер
        monitors_storage = application.bot_data.setdefault("active_monitors", {})
        user_data_storage = application.bot_data.setdefault("user_data_store", {})

        # Если из storage ничего не загружено, но есть данные в bot_data (после рестарта без смены образа), сохраним в storage
        if loaded == 0 and monitors_storage:
            try:
                if storage:
                    storage.save_all(monitors_storage)  # миграция в storage
                    safe_log_system("Выполнена миграция мониторингов из bot_data в storage", {"count": len(monitors_storage)})
            except Exception as e:
                safe_log_system("Ошибка миграции мониторингов в storage", {"error": str(e)}, level="error")

        # Теперь приводим активные мониторинги к данным менеджера
        if user_manager.active_monitors:
            # Загруженные из storage данные подставляем в bot_data
            monitors_storage.clear()
            monitors_storage.update(user_manager.active_monitors)
        else:
            # Иначе берем из bot_data (если были) и в менеджер
            user_manager.bind_active_monitors(monitors_storage)

        user_manager.bind_user_data_store(user_data_storage)
        active_monitors = user_manager.active_monitors
        user_data_store = user_manager.user_data_store

        # Добавляем фоновую задачу для очистки застрявших callbacks
        job_queue.run_repeating(
            cleanup_stuck_callbacks,
            interval=30,  # Проверка каждые 30 секунд
            first=10,     # Первый запуск через 10 секунд
            name=CLEANUP_JOB_NAME
        )

        safe_log_bot("Данные восстановлены", {
            "monitors_count": len(active_monitors),
            "mode": "memory-only",
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

        restart_info = application.bot_data.get("restart_info", {})
        if restart_info.get("pending"):
            safe_log_system("Перезапуск бота: выполняем рестарт процесса", restart_info)
            restart_info["pending"] = False
            logging.shutdown()
            os.execl(sys.executable, sys.executable, *sys.argv)

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
