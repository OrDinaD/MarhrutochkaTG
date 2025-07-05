#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности бота
"""

import asyncio
import logging
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.parser import FinalMarshrutochkaParser
from src.requests_auth import RequestsAuthManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_parser():
    """Тест парсера"""
    print("=== Тест парсера ===")
    
    try:
        async with FinalMarshrutochkaParser() as parser:
            print("Парсер инициализирован успешно")
            
            # Тест получения рейсов
            today = "2025-07-06"  # завтра
            routes_data = await parser.get_all_routes(today)
            
            print(f"Результат парсера: {routes_data}")
            
            if routes_data and routes_data.get('success'):
                print("✅ Парсер работает корректно")
            else:
                print("❌ Парсер не возвращает данные")
                
    except Exception as e:
        print(f"❌ Ошибка парсера: {e}")
        import traceback
        traceback.print_exc()

def test_requests_auth():
    """Тест менеджера авторизации"""
    print("\n=== Тест RequestsAuthManager ===")
    
    try:
        auth_manager = RequestsAuthManager()
        print("RequestsAuthManager инициализирован успешно")
        
        # Тест методов без авторизации
        print(f"is_authenticated: {auth_manager.is_authenticated}")
        
        profile = auth_manager.get_profile()
        print(f"get_profile (неавторизован): {profile}")
        
        tickets = auth_manager.get_tickets()
        print(f"get_tickets (неавторизован): {tickets}")
        
        print("✅ RequestsAuthManager работает корректно")
        
    except Exception as e:
        print(f"❌ Ошибка RequestsAuthManager: {e}")
        import traceback
        traceback.print_exc()

def test_bot_imports():
    """Тест импортов бота"""
    print("\n=== Тест импортов бота ===")
    
    try:
        from src import bot
        print("✅ Импорт src.bot успешен")
        
        # Тест функций
        user_id = 123456
        keyboard = bot.get_main_menu_keyboard(user_id)
        print(f"✅ get_main_menu_keyboard работает: {len(keyboard.inline_keyboard)} кнопок")
        
        # Тест с авторизованным пользователем
        auth_manager = RequestsAuthManager()
        auth_manager.is_authenticated = True
        bot.user_sessions[user_id] = auth_manager
        
        keyboard_auth = bot.get_main_menu_keyboard(user_id)
        print(f"✅ get_main_menu_keyboard для авторизованного: {len(keyboard_auth.inline_keyboard)} кнопок")
        
        # Очистка
        if user_id in bot.user_sessions:
            del bot.user_sessions[user_id]
            
    except Exception as e:
        print(f"❌ Ошибка импорта бота: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Основная функция тестирования"""
    print("🧪 Запуск комплексного тестирования бота...")
    
    try:
        test_requests_auth()
        test_bot_imports()
        await test_parser()
        
        print("\n✅ Все тесты завершены!")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
