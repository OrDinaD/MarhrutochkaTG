#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест телеграм-бота с использованием Telegram API
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import RetryAfter, Forbidden, NetworkError
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def send_test_command(bot, chat_id, command, description):
    """Отправка тестовой команды боту"""
    logger.info(f"🧪 Тестирование команды {command}: {description}")
    try:
        await bot.send_message(chat_id=chat_id, text=command)
        logger.info(f"✅ Команда {command} отправлена успешно")
        # Ждем немного, чтобы бот успел обработать команду
        await asyncio.sleep(1)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке команды {command}: {e}")
        return False

async def send_test_message(bot, chat_id, message, description):
    """Отправка тестового сообщения боту"""
    logger.info(f"🧪 Тестирование сообщения: {description}")
    try:
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"✅ Сообщение отправлено успешно")
        # Ждем немного, чтобы бот успел обработать сообщение
        await asyncio.sleep(1)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке сообщения: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем токен бота из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return
    
    # ID чата для тестирования
    test_chat_id = input("Введите ID чата для тестирования (ваш ID в Телеграм): ")
    try:
        test_chat_id = int(test_chat_id)
    except ValueError:
        logger.error("❌ Некорректный ID чата. Должно быть число.")
        return
    
    # Создаем экземпляр бота
    bot = Bot(token=token)
    
    logger.info(f"🚀 Начало тестирования бота с ID чата: {test_chat_id}")
    
    # Тестируем команду /start
    await send_test_command(bot, test_chat_id, "/start", "Команда запуска бота")
    await asyncio.sleep(2)  # Даем боту время на ответ
    
    # Тестируем команду /help
    await send_test_command(bot, test_chat_id, "/help", "Команда помощи")
    await asyncio.sleep(2)  # Даем боту время на ответ
    
    # Тестируем команду /monitoring
    await send_test_command(bot, test_chat_id, "/monitoring", "Команда мониторинга")
    await asyncio.sleep(2)  # Даем боту время на ответ
    
    logger.info("🏁 Тестирование команд завершено. Проверьте работу бота в Telegram.")
    
    # Выводим инструкции для ручного тестирования
    logger.info("""
🧪 Для полного тестирования бота вручную выполните следующие действия в Telegram:
1. Нажмите кнопку "🔍 Поиск рейсов" и проверьте работу поиска маршрутов
2. Нажмите кнопку "🔔 Настроить мониторинг" и пройдите весь процесс настройки
3. Нажмите кнопку "📊 Мои мониторинги" и проверьте отображение активных мониторингов
4. Нажмите кнопку "🔒 Войти в аккаунт" и проверьте процесс авторизации
5. После авторизации проверьте кнопку "👤 Мой профиль" для просмотра профиля
6. Проверьте кнопку "🎫 Мои билеты" для просмотра билетов
7. Проверьте кнопку "🔓 Выйти из аккаунта" для выхода из аккаунта
8. Проверьте кнопку "❓ Помощь" для получения справки
""")

if __name__ == "__main__":
    asyncio.run(main())
