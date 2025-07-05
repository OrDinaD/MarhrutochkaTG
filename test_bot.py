#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности бота
"""

import asyncio
import logging
from src.bot import get_main_menu_keyboard, user_sessions
from src.requests_auth import RequestsAuthManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_main_menu_keyboard():
    """Тест генерации клавиатуры главного меню"""
    print("=== Тест главного меню ===")
    
    # Тест для неавторизованного пользователя
    user_id = 123456
    keyboard = get_main_menu_keyboard(user_id)
    
    print("Клавиатура для неавторизованного пользователя:")
    for row in keyboard.inline_keyboard:
        for button in row:
            print(f"  - {button.text} ({button.callback_data})")
    
    # Тест для авторизованного пользователя
    user_sessions[user_id] = RequestsAuthManager()
    user_sessions[user_id].is_authenticated = True
    
    keyboard_auth = get_main_menu_keyboard(user_id)
    
    print("\nКлавиатура для авторизованного пользователя:")
    for row in keyboard_auth.inline_keyboard:
        for button in row:
            print(f"  - {button.text} ({button.callback_data})")
    
    # Очистка
    if user_id in user_sessions:
        del user_sessions[user_id]

def test_requests_auth_manager():
    """Тест RequestsAuthManager"""
    print("\n=== Тест RequestsAuthManager ===")
    
    auth_manager = RequestsAuthManager()
    
    # Тест методов
    print(f"is_authenticated: {auth_manager.is_authenticated}")
    
    # Тест метода get_profile
    try:
        profile = auth_manager.get_profile()
        print(f"get_profile() вернул: {profile}")
    except Exception as e:
        print(f"get_profile() вызвал исключение: {e}")
    
    # Тест метода get_tickets
    try:
        tickets = auth_manager.get_tickets()
        print(f"get_tickets() вернул: {tickets}")
    except Exception as e:
        print(f"get_tickets() вызвал исключение: {e}")

def main():
    """Основная функция тестирования"""
    print("🧪 Запуск тестов бота...")
    
    try:
        test_main_menu_keyboard()
        test_requests_auth_manager()
        
        print("\n✅ Все тесты завершены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
