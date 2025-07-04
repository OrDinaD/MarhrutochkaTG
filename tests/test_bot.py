#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Telegram-бота
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Загружаем переменные окружения
load_dotenv()

async def test_bot_connection():
    """Тест подключения к Telegram-боту"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ Токен не найден в файле .env")
        return False
    
    try:
        bot = Bot(token)
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        
        print(f"✅ Подключение к боту успешно!")
        print(f"🤖 Имя бота: {bot_info.first_name}")
        print(f"🔗 Username: @{bot_info.username}")
        print(f"🆔 ID: {bot_info.id}")
        
        return True
        
    except TelegramError as e:
        print(f"❌ Ошибка подключения к Telegram: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование Telegram-бота...")
    print("=" * 50)
    
    # Проверяем подключение к боту
    connection_ok = await test_bot_connection()
    
    if connection_ok:
        print("\n✅ Все тесты пройдены успешно!")
        print("🚀 Бот готов к запуску!")
        print("\nДля запуска бота используйте:")
        print("./scripts/start_bot.sh")
    else:
        print("\n❌ Тесты не пройдены")
        print("Проверьте настройки в файле .env")

if __name__ == "__main__":
    asyncio.run(main())
