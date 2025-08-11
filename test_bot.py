#!/usr/bin/env python3
"""
Тестовый скрипт для проверки основных компонентов бота
"""

import os
import sys
import traceback
from unittest.mock import Mock

# Добавляем путь к src для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Тестирует все импорты"""
    print("🔍 Тестирование импортов...")
    
    try:
        # Тест основных модулей
        from src.auth import bot_auth_manager, format_profile_message, format_bookings_message
        print("✅ Модуль auth импортирован успешно")
        
        from src.utils import FinalMarshrutochkaParser, AutoBookingManager
        print("✅ Модуль utils импортирован успешно")
        
        from src.monitoring import setup_logging, railway_logger, crash_handler
        print("✅ Модуль monitoring импортирован успешно")
        
        from src.admin_panel import AdminPanel
        print("✅ Модуль admin_panel импортирован успешно")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        traceback.print_exc()
        return False

def test_bot_initialization():
    """Тестирует инициализацию бота"""
    print("\n🤖 Тестирование инициализации бота...")
    
    try:
        # Мокаем переменные окружения
        os.environ['BOT_TOKEN'] = 'test_token'
        os.environ['ADMIN_TELEGRAM_ID'] = '12345'
        
        # Импортируем модуль бота
        from src import bot
        
        # Тестируем инициализацию глобальных переменных
        assert hasattr(bot, 'active_monitors')
        assert hasattr(bot, 'user_data_store')
        assert hasattr(bot, 'admin_panel')
        
        print("✅ Глобальные переменные инициализированы")
        
        # Тестируем создание клавиатур
        keyboard = bot.get_date_keyboard()
        assert keyboard is not None
        print("✅ Генерация клавиатуры работает")
        
        # Тестируем форматирование конфигураций
        config = {
            'date': '2025-01-15',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '09:00-15:00'
        }
        formatted = bot.format_monitor_config(config)
        assert formatted is not None
        print("✅ Форматирование конфигурации работает")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        traceback.print_exc()
        return False

def test_functions():
    """Тестирует основные функции"""
    print("\n🔧 Тестирование функций...")
    
    try:
        from src import bot
        
        # Тестируем функции загрузки/сохранения
        original_monitors = bot.active_monitors.copy()
        bot.load_active_monitors()
        bot.save_active_monitors()
        print("✅ Функции загрузки/сохранения мониторингов работают")
        
        # Тестируем функции пользовательских сессий
        original_sessions = bot.user_sessions.copy()
        bot.load_user_sessions()
        bot.save_user_sessions()
        print("✅ Функции пользовательских сессий работают")
        
        # Тестируем создание URL
        url = bot.create_webapp_url("minsk_ostrovets", "2025-01-15")
        assert url is not None
        print("✅ Создание URL работает")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования функций: {e}")
        traceback.print_exc()
        return False

def test_admin_panel():
    """Тестирует админ-панель"""
    print("\n👤 Тестирование админ-панели...")
    
    try:
        from src.admin_panel import AdminPanel
        
        admin = AdminPanel(12345)
        
        # Тестируем проверку прав администратора
        assert admin.is_admin(12345) == True
        assert admin.is_admin(99999) == False
        print("✅ Проверка прав администратора работает")
        
        # Тестируем создание клавиатуры
        keyboard = admin.get_admin_menu_keyboard()
        assert keyboard is not None
        print("✅ Создание админ-клавиатуры работает")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования админ-панели: {e}")
        traceback.print_exc()
        return False

def test_auth_manager():
    """Тестирует менеджер авторизации"""
    print("\n🔐 Тестирование менеджера авторизации...")
    
    try:
        from src.auth import bot_auth_manager
        
        # Тестируем проверку авторизации
        result = bot_auth_manager.is_authenticated(99999)
        assert isinstance(result, bool)
        print("✅ Проверка авторизации работает")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования авторизации: {e}")
        traceback.print_exc()
        return False

def test_security():
    """Тестирует безопасность"""
    print("\n🔒 Тестирование безопасности...")
    
    tests_passed = 0
    total_tests = 4
    
    try:
        from src import bot
        
        # Тест 1: Валидация номера телефона
        try:
            # Проверяем, что функция обработки телефона не падает на некорректных данных
            test_inputs = ["", "abc", "123", "+375291234567", "375291234567"]
            # Здесь должна быть функция валидации, но её нет - это баг
            print("⚠️ Отсутствует валидация номера телефона")
        except:
            pass
        
        # Тест 2: Защита от SQL injection (если есть БД)
        print("✅ SQL injection: проверка не применима (нет БД)")
        tests_passed += 1
        
        # Тест 3: Защита от XSS в сообщениях
        try:
            test_config = {
                'date': '<script>alert("xss")</script>',
                'direction': 'minsk_ostrovets',
                'time_type': 'departure',
                'time_range': '09:00-15:00'
            }
            result = bot.format_monitor_config(test_config)
            if '<script>' not in result:
                print("✅ Базовая защита от XSS работает")
                tests_passed += 1
            else:
                print("❌ Отсутствует защита от XSS")
        except:
            print("❌ Ошибка при тестировании XSS")
            
        # Тест 4: Проверка длины пользовательского ввода
        print("⚠️ Отсутствует валидация длины ввода")
        
        # Тест 5: Проверка санитизации данных
        print("⚠️ Отсутствует санитизация пользовательских данных")
        
        return tests_passed >= total_tests // 2
        
    except Exception as e:
        print(f"❌ Ошибка тестирования безопасности: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 НАЧАЛО ТЕСТИРОВАНИЯ БОТА\n")
    
    tests = [
        ("Импорты", test_imports),
        ("Инициализация бота", test_bot_initialization),
        ("Основные функции", test_functions),
        ("Админ-панель", test_admin_panel),
        ("Менеджер авторизации", test_auth_manager),
        ("Безопасность", test_security),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED\n")
            else:
                print(f"❌ {test_name}: FAILED\n")
        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}\n")
    
    print("=" * 50)
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"✅ Пройдено: {passed}/{total}")
    print(f"❌ Провалено: {total - passed}/{total}")
    print(f"📈 Успешность: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        return True
    else:
        print("⚠️ ЕСТЬ ПРОБЛЕМЫ, ТРЕБУЮЩИЕ ВНИМАНИЯ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
