#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Полноценный тест бота с авторизацией в Telegram
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_bot_auth_flow(bot, chat_id):
    """Тестирование полного процесса авторизации"""
    logger.info("🧪 Начинаем тест процесса авторизации")
    
    # 1. Отправляем команду /start
    logger.info("1. Отправляем /start")
    await bot.send_message(chat_id=chat_id, text="/start")
    await asyncio.sleep(2)
    
    # 2. Нажимаем кнопку "Войти в аккаунт"
    logger.info("2. Эмулируем нажатие кнопки 'Войти в аккаунт'")
    await bot.send_message(
        chat_id=chat_id,
        text="🧪 Тест: Нажимаем кнопку 'Войти в аккаунт'"
    )
    await asyncio.sleep(2)
    
    # 3. Отправляем номер телефона
    logger.info("3. Отправляем номер телефона")
    await bot.send_message(chat_id=chat_id, text="+375299605390")
    await asyncio.sleep(2)
    
    # 4. Отправляем пароль
    logger.info("4. Отправляем пароль")
    await bot.send_message(chat_id=chat_id, text="Я Zxcvbnm,1")
    await asyncio.sleep(5)
    
    # 5. Тестируем команды после авторизации
    logger.info("5. Тестируем команды после авторизации")
    await asyncio.sleep(2)
    
    # Эмулируем нажатие кнопки "Мой профиль"
    logger.info("6. Эмулируем нажатие кнопки 'Мой профиль'")
    await bot.send_message(
        chat_id=chat_id,
        text="🧪 Тест: Нажимаем кнопку 'Мой профиль'"
    )
    await asyncio.sleep(3)
    
    # Эмулируем нажатие кнопки "Мои билеты"
    logger.info("7. Эмулируем нажатие кнопки 'Мои билеты'")
    await bot.send_message(
        chat_id=chat_id,
        text="🧪 Тест: Нажимаем кнопку 'Мои билеты'"
    )
    await asyncio.sleep(3)
    
    logger.info("✅ Тест авторизации завершен")

async def test_bot_search(bot, chat_id):
    """Тестирование поиска рейсов"""
    logger.info("🧪 Тестируем поиск рейсов")
    
    # Отправляем дату в формате YYYY-MM-DD
    test_date = "2025-07-10"
    logger.info(f"Отправляем дату для поиска: {test_date}")
    await bot.send_message(chat_id=chat_id, text=test_date)
    await asyncio.sleep(5)
    
    logger.info("✅ Тест поиска завершен")

async def test_bot_monitoring(bot, chat_id):
    """Тестирование настройки мониторинга"""
    logger.info("🧪 Тестируем настройку мониторинга")
    
    # Отправляем команду /monitoring
    await bot.send_message(chat_id=chat_id, text="/monitoring")
    await asyncio.sleep(3)
    
    logger.info("✅ Тест мониторинга завершен")

async def main():
    """Основная функция тестирования"""
    # Загрузка переменных окружения
    load_dotenv()
    
    # Получение токена
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден")
        return
    
    # ID чата для тестирования
    chat_id = int(input("Введите ваш Telegram ID: "))
    
    # Создание экземпляра бота
    bot = Bot(token=token)
    
    logger.info(f"🚀 Начинаем полноценное тестирование бота с ID чата: {chat_id}")
    
    # Тестируем авторизацию
    await test_bot_auth_flow(bot, chat_id)
    
    await asyncio.sleep(3)
    
    # Тестируем поиск рейсов
    await test_bot_search(bot, chat_id)
    
    await asyncio.sleep(3)
    
    # Тестируем мониторинг
    await test_bot_monitoring(bot, chat_id)
    
    logger.info("🏁 Все тесты завершены. Проверьте работу бота в Telegram.")
    
    # Инструкции для ручного тестирования
    print("""
📋 ИНСТРУКЦИИ ДЛЯ РУЧНОГО ТЕСТИРОВАНИЯ:

1. Проверьте, что команда /start работает и отображается главное меню
2. Нажмите кнопку "🔒 Войти в аккаунт" и пройдите процесс авторизации
3. Проверьте, что после входа появляются новые кнопки:
   - 👤 Мой профиль
   - 🎫 Мои билеты
   - 🔓 Выйти из аккаунта
4. Нажмите "👤 Мой профиль" и убедитесь, что данные отображаются
5. Нажмите "🎫 Мои билеты" и проверьте список билетов
6. Проверьте поиск рейсов, отправив дату в формате YYYY-MM-DD
7. Протестируйте настройку мониторинга через кнопку "🔔 Настроить мониторинг"
8. Проверьте команду /monitoring для управления активными мониторингами
9. Проверьте кнопку "🔓 Выйти из аккаунта"
10. Убедитесь, что после выхода меню возвращается к исходному состоянию

💡 ОЖИДАЕМОЕ ПОВЕДЕНИЕ:
- Бот должен корректно обрабатывать все команды
- Авторизация должна работать с вашими реальными данными
- Профиль должен отображать актуальную информацию
- Билеты должны показывать реальные бронирования
- Поиск рейсов должен возвращать актуальные данные
- Мониторинг должен настраиваться и работать в фоне
""")

if __name__ == "__main__":
    asyncio.run(main())
