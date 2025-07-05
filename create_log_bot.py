#!/usr/bin/env python3
"""
Скрипт для создания бота-логгера и получения токена и chat_id
"""

import sys
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Пытаемся получить токен из переменных окружения или используем переданный параметр
BOT_TOKEN = os.getenv('LOG_BOT_TOKEN')

if not BOT_TOKEN and len(sys.argv) > 1:
    BOT_TOKEN = sys.argv[1]

if not BOT_TOKEN:
    logger.error("Токен бота не найден! Укажите его через переменную LOG_BOT_TOKEN или первым аргументом командной строки.")
    logger.info("Пример: python create_log_bot.py 'YOUR_TOKEN'")
    sys.exit(1)

chat_ids = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    chat_ids.add(chat_id)
    
    await update.message.reply_text(
        f"👋 Привет, {user.full_name}!\n\n"
        f"✅ Бот для логирования настроен и готов к работе.\n"
        f"📱 Ваш Chat ID: `{chat_id}`\n\n"
        "ℹ️ Этот бот будет отправлять сюда логи вашего основного бота.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Новый пользователь: {user.full_name} (ID: {user.id}), Chat ID: {chat_id}")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /id для получения ID чата"""
    chat_id = update.effective_chat.id
    chat_ids.add(chat_id)
    
    await update.message.reply_text(
        f"📱 Ваш Chat ID: `{chat_id}`\n\n"
        "Используйте этот ID в переменной окружения LOG_CHAT_ID.",
        parse_mode='Markdown'
    )

async def test_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тестовый обработчик для проверки логирования"""
    await update.message.reply_text("📤 Отправляю тестовые сообщения...")
    
    await update.message.reply_text("🟢 Тестовое ИНФО сообщение")
    await update.message.reply_text("🟠 Тестовое ПРЕДУПРЕЖДЕНИЕ")
    await update.message.reply_text("🔴 Тестовая ОШИБКА")
    
    await update.message.reply_text("✅ Тестирование завершено!")

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    await update.message.reply_text(
        "🤖 **Бот для логирования**\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "/id - Получить ID текущего чата\n"
        "/test - Отправить тестовые сообщения\n"
        "/help - Показать это сообщение\n\n"
        "Для настройки логирования добавьте следующие переменные окружения "
        "в ваш основной проект:\n"
        "```\n"
        f"LOG_BOT_TOKEN={BOT_TOKEN}\n"
        "LOG_CHAT_ID=ваш_чат_id\n"
        "```",
        parse_mode='Markdown'
    )

def main() -> None:
    """Запуск бота."""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", get_id))
    application.add_handler(CommandHandler("test", test_log))
    application.add_handler(CommandHandler("help", show_help))

    # Запускаем бота
    logger.info("🚀 Запуск бота для логирования...")
    logger.info(f"🔑 Token: {BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}")
    
    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)
    finally:
        logger.info("Активные чаты:")
        for chat_id in chat_ids:
            logger.info(f"Chat ID: {chat_id}")

if __name__ == "__main__":
    main()
