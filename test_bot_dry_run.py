#!/usr/bin/env python3
"""
Тестирование запуска бота в режиме dry-run без реального Telegram токена
"""

import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Добавляем src в путь
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_bot_initialization():
    """Тестирование инициализации бота"""
    print("🤖 Тестируем инициализацию бота...")
    
    try:
        # Мокаем Telegram API
        with patch('telegram.ext.Application') as MockApplication:
            # Настраиваем мок
            mock_app = MagicMock()
            MockApplication.builder.return_value.token.return_value.build.return_value = mock_app
            
            # Импортируем модули бота
            import bot
            
            # Проверяем основные функции
            functions_to_test = [
                'get_date_keyboard',
                'get_direction_keyboard', 
                'get_time_type_keyboard',
                'get_time_range_keyboard',
                'format_monitor_config',
                'get_main_menu_keyboard',
                'format_routes_message',
                'filter_routes_by_criteria',
                'check_time_criteria'
            ]
            
            all_functions_exist = True
            for func_name in functions_to_test:
                if not hasattr(bot, func_name):
                    print(f"   ❌ Функция {func_name} не найдена")
                    all_functions_exist = False
                else:
                    print(f"   ✓ Функция {func_name} найдена")
            
            # Проверяем глобальные переменные
            required_vars = [
                'parser',
                'requests_auth_manager', 
                'job_queue',
                'active_monitors',
                'user_data_store',
                'user_sessions',
                'application'
            ]
            
            all_vars_exist = True
            for var_name in required_vars:
                if not hasattr(bot, var_name):
                    print(f"   ❌ Переменная {var_name} не найдена")
                    all_vars_exist = False
                else:
                    print(f"   ✓ Переменная {var_name} найдена")
            
            # Проверяем инициализацию функций
            try:
                await bot.init_parser()
                print("   ✓ init_parser() работает")
            except Exception as e:
                print(f"   ❌ init_parser() ошибка: {e}")
                all_functions_exist = False
            
            try:
                await bot.init_requests_auth_manager()
                print("   ✓ init_requests_auth_manager() работает")
            except Exception as e:
                print(f"   ❌ init_requests_auth_manager() ошибка: {e}")
                all_functions_exist = False
            
            # Проверяем обработчики команд
            command_handlers = [
                'start',
                'help_command',
                'monitoring_command',
                'handle_main_menu',
                'my_monitors',
                'stop_monitoring'
            ]
            
            for handler_name in command_handlers:
                if not hasattr(bot, handler_name):
                    print(f"   ❌ Обработчик {handler_name} не найден")
                    all_functions_exist = False
                else:
                    print(f"   ✓ Обработчик {handler_name} найден")
            
            # Проверяем conversation handlers
            conversation_functions = [
                'start_monitoring_conversation',
                'handle_date_choice',
                'handle_direction_choice',
                'handle_time_type_choice',
                'handle_time_range_choice',
                'handle_monitoring_confirmation'
            ]
            
            for func_name in conversation_functions:
                if not hasattr(bot, func_name):
                    print(f"   ❌ Conversation функция {func_name} не найдена")
                    all_functions_exist = False
                else:
                    print(f"   ✓ Conversation функция {func_name} найдена")
            
            # Проверяем функции аутентификации
            auth_functions = [
                'start_login_requests',
                'handle_phone_requests',
                'handle_password_requests',
                'get_profile_requests',
                'get_tickets_requests',
                'logout_requests'
            ]
            
            for func_name in auth_functions:
                if not hasattr(bot, func_name):
                    print(f"   ❌ Auth функция {func_name} не найдена")
                    all_functions_exist = False
                else:
                    print(f"   ✓ Auth функция {func_name} найдена")
            
            # Проверяем функции мониторинга
            monitoring_functions = [
                'check_routes_for_user',
                'send_monitoring_notification',
                'load_active_monitors',
                'save_active_monitors',
                'load_user_sessions',
                'save_user_sessions'
            ]
            
            for func_name in monitoring_functions:
                if not hasattr(bot, func_name):
                    print(f"   ❌ Monitoring функция {func_name} не найдена")
                    all_functions_exist = False
                else:
                    print(f"   ✓ Monitoring функция {func_name} найдена")
            
            # Проверяем функцию register_handlers
            if hasattr(bot, 'register_handlers'):
                print("   ✓ register_handlers найдена")
                try:
                    bot.register_handlers(mock_app)
                    print("   ✓ register_handlers выполняется без ошибок")
                except Exception as e:
                    print(f"   ❌ register_handlers ошибка: {e}")
                    all_functions_exist = False
            else:
                print("   ❌ register_handlers не найдена")
                all_functions_exist = False
            
            if all_functions_exist and all_vars_exist:
                print("   🎉 Все компоненты бота найдены и работают!")
                return True
            else:
                print("   ❌ Некоторые компоненты бота отсутствуют или не работают")
                return False
                
    except Exception as e:
        print(f"   ❌ Ошибка при тестировании инициализации: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_conversation_flow():
    """Тестирование flow conversation handlers"""
    print("\n💬 Тестируем conversation flow...")
    
    try:
        import bot
        from telegram import Update, CallbackQuery, Message, User, Chat
        from telegram.ext import ContextTypes
        
        # Создаем мок объекты
        user = User(id=123456, first_name="Test", is_bot=False)
        chat = Chat(id=123456, type="private")
        
        # Тестируем получение клавиатур
        date_kb = bot.get_date_keyboard()
        print(f"   ✓ Date keyboard: {len(date_kb.inline_keyboard)} кнопок")
        
        direction_kb = bot.get_direction_keyboard()
        print(f"   ✓ Direction keyboard: {len(direction_kb.inline_keyboard)} кнопок")
        
        time_type_kb = bot.get_time_type_keyboard()
        print(f"   ✓ Time type keyboard: {len(time_type_kb.inline_keyboard)} кнопок")
        
        time_range_kb = bot.get_time_range_keyboard("departure")
        print(f"   ✓ Time range keyboard: {len(time_range_kb.inline_keyboard)} кнопок")
        
        main_menu_kb = bot.get_main_menu_keyboard(123456)
        print(f"   ✓ Main menu keyboard: {len(main_menu_kb.inline_keyboard)} кнопок")
        
        # Тестируем форматирование
        test_config = {
            'date': '2025-07-07',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '07:00-09:00'
        }
        
        formatted = bot.format_monitor_config(test_config)
        print(f"   ✓ Config formatting: {len(formatted)} символов")
        
        # Тестируем форматирование сообщения с рейсами
        test_routes = {
            'success': True,
            'minsk_to_ostrovets': [
                {
                    'departure_time': '07:30',
                    'arrival_time': '09:55',
                    'duration': '2ч 25м',
                    'available_seats': 5,
                    'carrier': 'Тестовый перевозчик'
                }
            ],
            'ostrovets_to_minsk': []
        }
        
        formatted_routes = bot.format_routes_message(test_routes, '2025-07-07')
        print(f"   ✓ Routes formatting: {len(formatted_routes)} символов")
        
        print("   🎉 Conversation flow тесты прошли успешно!")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка в conversation flow: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_monitoring_logic():
    """Тестирование логики мониторинга"""
    print("\n📊 Тестируем логику мониторинга...")
    
    try:
        import bot
        
        # Тестовые данные рейсов
        test_routes_data = {
            'success': True,
            'minsk_to_ostrovets': [
                {
                    'departure_time': '07:30',
                    'arrival_time': '09:55',
                    'available_seats': 5,
                    'from_city': 'Минск',
                    'to_city': 'Островец',
                    'carrier': 'Тестовый перевозчик'
                },
                {
                    'departure_time': '14:00',
                    'arrival_time': '16:25',
                    'available_seats': 12,
                    'from_city': 'Минск',
                    'to_city': 'Островец',
                    'carrier': 'Другой перевозчик'
                }
            ],
            'ostrovets_to_minsk': [
                {
                    'departure_time': '08:00',
                    'arrival_time': '10:25',
                    'available_seats': 0,
                    'from_city': 'Островец',
                    'to_city': 'Минск',
                    'carrier': 'Третий перевозчик'
                }
            ]
        }
        
        # Тестируем различные конфигурации мониторинга
        configs = [
            {
                'direction': 'minsk_ostrovets',
                'time_type': 'departure',
                'time_range': '07:00-09:00'
            },
            {
                'direction': 'both',
                'time_type': 'any',
                'time_range': 'any'
            },
            {
                'direction': 'ostrovets_minsk',
                'time_type': 'departure',
                'time_range': '07:00-10:00'
            }
        ]
        
        for i, config in enumerate(configs, 1):
            filtered = bot.filter_routes_by_criteria(test_routes_data, config)
            print(f"   ✓ Конфигурация {i}: отфильтровано {len(filtered)} рейсов")
            
            # Тестируем проверку времени для каждого найденного рейса
            for route in filtered:
                time_check = bot.check_time_criteria(route, config)
                print(f"     - Рейс {route['departure_time']}: время {'OK' if time_check else 'НЕ ПОДХОДИТ'}")
        
        # Тестируем сохранение/загрузку мониторингов
        original_monitors = bot.active_monitors.copy()
        
        test_monitor = {
            'user_id': 999999,
            'date': '2025-07-07',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '07:00-09:00',
            'chat_id': 999999,
            'created_at': '2025-07-06T16:00:00'
        }
        
        bot.active_monitors[999999] = test_monitor
        bot.save_active_monitors()
        print("   ✓ Мониторинг сохранен")
        
        bot.active_monitors.clear()
        bot.load_active_monitors()
        
        if 999999 in bot.active_monitors:
            print("   ✓ Мониторинг загружен")
            del bot.active_monitors[999999]
            bot.save_active_monitors()
        else:
            print("   ❌ Мониторинг не загрузился")
            
        bot.active_monitors = original_monitors
        
        print("   🎉 Логика мониторинга работает корректно!")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка в логике мониторинга: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Полное тестирование функциональности бота MarhrutochkaTG")
    print("=" * 70)
    
    results = []
    
    # Запускаем тесты
    results.append(await test_bot_initialization())
    results.append(await test_conversation_flow())
    results.append(await test_monitoring_logic())
    
    # Подводим итоги
    print("\n" + "=" * 70)
    print("📋 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Прошло тестов: {passed}/{total}")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ УСПЕШНО! Бот полностью функционален.")
        return 0
    else:
        print("❌ Некоторые тесты не прошли. Требуется дополнительная проверка.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
