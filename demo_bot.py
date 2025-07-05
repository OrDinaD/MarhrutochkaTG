#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации работы бота
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockUpdate:
    """Мок объект Update для тестирования"""
    def __init__(self, user_id: int = 123456789):
        self.effective_user = MockUser(user_id)
        self.message = MockMessage()
        self.callback_query = None

class MockUser:
    """Мок объект User"""
    def __init__(self, user_id: int):
        self.id = user_id
        self.first_name = "Test"
        self.last_name = "User"
        self.username = "testuser"

class MockMessage:
    """Мок объект Message"""
    def __init__(self):
        self.text = "/start"
        self.message_id = 1
        
    async def reply_text(self, text: str, reply_markup=None, parse_mode=None):
        print(f"BOT REPLY: {text}")
        if reply_markup:
            print("KEYBOARD:")
            for row in reply_markup.inline_keyboard:
                for button in row:
                    print(f"  [{button.text}] -> {button.callback_data}")
        return self

class MockContext:
    """Мок объект Context"""
    def __init__(self):
        self.bot = MockBot()
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}
        self.error = None

class MockBot:
    """Мок объект Bot"""
    def __init__(self):
        pass
    
    async def send_message(self, chat_id: int, text: str, reply_markup=None, parse_mode=None):
        print(f"BOT MESSAGE TO {chat_id}: {text}")
        if reply_markup:
            print("KEYBOARD:")
            for row in reply_markup.inline_keyboard:
                for button in row:
                    print(f"  [{button.text}] -> {button.callback_data}")
        return MockMessage()

async def test_bot_functionality():
    """Тестирование функций бота"""
    print("🤖 Тестирование функциональности бота...")
    print("=" * 50)
    
    try:
        # Импортируем функции бота
        from bot import start, get_main_menu_keyboard, user_sessions
        
        # Тестируем генерацию клавиатуры
        print("\n📋 Тестирование клавиатуры главного меню:")
        print("-" * 30)
        
        # Клавиатура для неавторизованного пользователя
        keyboard = get_main_menu_keyboard(123456789)
        print("Неавторизованный пользователь:")
        for row in keyboard.inline_keyboard:
            for button in row:
                print(f"  [{button.text}] -> {button.callback_data}")
        
        # Симулируем авторизованного пользователя
        from requests_auth import RequestsAuthManager
        auth_manager = RequestsAuthManager()
        user_sessions[123456789] = auth_manager
        
        keyboard_auth = get_main_menu_keyboard(123456789)
        print("\nАвторизованный пользователь:")
        for row in keyboard_auth.inline_keyboard:
            for button in row:
                print(f"  [{button.text}] -> {button.callback_data}")
        
        # Тестируем команду /start
        print("\n🚀 Тестирование команды /start:")
        print("-" * 30)
        
        mock_update = MockUpdate()
        mock_context = MockContext()
        
        await start(mock_update, mock_context)
        
        print("\n✅ Тестирование завершено успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

async def test_search_functionality():
    """Тестирование функции поиска"""
    print("\n🔍 Тестирование функции поиска:")
    print("-" * 30)
    
    try:
        from parser import FinalMarshrutochkaParser
        
        async with FinalMarshrutochkaParser() as parser:
            # Поиск маршрутов
            from datetime import datetime, timedelta
            today = datetime.now()
            date_str = today.strftime('%Y-%m-%d')
            
            routes = await parser.search_routes("Минск", "Островец", date_str)
            print(f"✅ Найдено маршрутов: {len(routes)}")
            
            if routes:
                print("Первые 3 маршрута:")
                for i, route in enumerate(routes[:3]):
                    print(f"{i+1}. {route['departure_time']} -> {route['arrival_time']}, "
                          f"мест: {route['available_seats']}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании поиска: {e}")

async def test_monitoring_functions():
    """Тестирование функций мониторинга"""
    print("\n📊 Тестирование функций мониторинга:")
    print("-" * 30)
    
    try:
        from bot import active_monitors, save_active_monitors, load_active_monitors
        
        # Тестируем сохранение/загрузку
        test_monitor = {
            'from_city': 'Минск',
            'to_city': 'Островец',
            'date': '2024-01-01',
            'time_filter': 'morning',
            'seats_threshold': 5
        }
        
        active_monitors[123456789] = test_monitor
        save_active_monitors()
        print("✅ Мониторинг сохранен")
        
        # Очищаем и загружаем обратно
        active_monitors.clear()
        load_active_monitors()
        
        if 123456789 in active_monitors:
            print("✅ Мониторинг загружен")
            print(f"Мониторинг: {active_monitors[123456789]}")
        else:
            print("⚠️ Мониторинг не загружен")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании мониторинга: {e}")

async def main():
    """Основная функция"""
    print("🚀 Демонстрация функциональности Telegram-бота")
    print("=" * 50)
    
    # Проверяем переменные окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ Токен бота не найден в переменных окружения")
        return
    
    print(f"✅ Токен бота найден (длина: {len(token)})")
    
    # Запускаем тесты
    await test_bot_functionality()
    await test_search_functionality()
    await test_monitoring_functions()
    
    print("\n" + "=" * 50)
    print("✅ Демонстрация завершена!")
    print("\nДля запуска бота выполните:")
    print("python src/bot.py")

if __name__ == "__main__":
    asyncio.run(main())
