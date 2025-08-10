#!/usr/bin/env python3
"""
Единый тестовый файл для всех функций бота MarhrutochkaTG
Объединяет все необходимые тесты в одном месте
"""

import asyncio
import os
import sys
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any

# Добавляем src в путь
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Настройка логирования для тестов
logging.basicConfig(
    level=logging.WARNING,  # Меньше шума во время тестов
    format='%(levelname)s: %(message)s'
)

class CompleteBotTester:
    """Полный тестер всех функций бота"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
    
    def log_test_start(self, test_name: str):
        """Логирование начала теста"""
        print(f"🧪 Тест: {test_name}")
    
    def log_test_result(self, test_name: str, status: str, details: str = ""):
        """Логирование результата теста"""
        emoji = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '🔥'
        print(f"{emoji} {test_name}: {status}")
        if details:
            print(f"   {details}")
    
    async def test_parser(self):
        """Тест парсера расписаний"""
        test_name = "Parser"
        self.log_test_start(test_name)
        
        try:
            from src.parser import FinalMarshrutochkaParser
            
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            async with FinalMarshrutochkaParser() as parser:
                routes = await parser.get_all_routes(tomorrow)
            
            if routes.get('success', False):
                total_routes = len(routes.get('minsk_to_ostrovets', [])) + len(routes.get('ostrovets_to_minsk', []))
                self.test_results['parser'] = {
                    'status': 'PASS',
                    'routes_found': total_routes,
                    'details': f"Найдено маршрутов: {total_routes}"
                }
                self.log_test_result(test_name, 'PASS', f"Найдено маршрутов: {total_routes}")
            else:
                self.test_results['parser'] = {
                    'status': 'FAIL',
                    'error': routes.get('error', 'Неизвестная ошибка')
                }
                self.log_test_result(test_name, 'FAIL', routes.get('error', 'Неизвестная ошибка'))
                
        except Exception as e:
            self.test_results['parser'] = {'status': 'ERROR', 'error': str(e)}
            self.log_test_result(test_name, 'ERROR', str(e))
    
    def test_environment(self):
        """Тест переменных окружения и конфигурации"""
        test_name = "Environment"
        self.log_test_start(test_name)
        
        try:
            # Проверяем токен бота
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not token or len(token) < 40:
                raise ValueError("TELEGRAM_BOT_TOKEN не найден или некорректен")
            
            # Проверяем обязательные файлы
            required_files = [
                'src/bot.py',
                'src/parser.py',
                'src/bot_auth_manager.py',
                'requirements.txt'
            ]
            
            missing_files = []
            for file in required_files:
                if not os.path.exists(file):
                    missing_files.append(file)
            
            if missing_files:
                raise FileNotFoundError(f"Отсутствуют файлы: {', '.join(missing_files)}")
            
            self.test_results['environment'] = {
                'status': 'PASS',
                'details': f"Токен: {len(token)} символов, файлы: OK"
            }
            self.log_test_result(test_name, 'PASS', f"Токен: {len(token)} символов, файлы: OK")
            
        except Exception as e:
            self.test_results['environment'] = {'status': 'ERROR', 'error': str(e)}
            self.log_test_result(test_name, 'ERROR', str(e))
    
    def test_bot_imports(self):
        """Тест импортов модулей бота"""
        test_name = "Bot Imports"
        self.log_test_start(test_name)
        
        try:
            # Тестируем импорты основных модулей
            from src import bot
            from src.parser import FinalMarshrutochkaParser
            from src.bot_auth_manager import bot_auth_manager
            from src.admin_panel import AdminPanel
            from src.auto_booking import AutoBookingManager
            
            self.test_results['bot_imports'] = {
                'status': 'PASS',
                'details': "Все модули импортированы успешно"
            }
            self.log_test_result(test_name, 'PASS', "Все модули импортированы успешно")
            
        except Exception as e:
            self.test_results['bot_imports'] = {'status': 'ERROR', 'error': str(e)}
            self.log_test_result(test_name, 'ERROR', str(e))
    
    def test_bot_functions(self):
        """Тест основных функций бота"""
        test_name = "Bot Functions"
        self.log_test_start(test_name)
        
        try:
            from src import bot
            
            # Тест создания клавиатуры
            test_user_id = 123456
            keyboard = bot.get_main_menu_keyboard(test_user_id)
            
            if not keyboard or not hasattr(keyboard, 'inline_keyboard'):
                raise ValueError("Клавиатура не создана корректно")
            
            buttons_count = len(keyboard.inline_keyboard)
            
            # Тест форматирования сообщений
            test_routes = {
                'success': True,
                'minsk_to_ostrovets': [
                    {
                        'departure_time': '08:00',
                        'arrival_time': '09:30',
                        'free_seats': 5,
                        'price': '12.50'
                    }
                ],
                'ostrovets_to_minsk': []
            }
            
            formatted_message = bot.format_routes_message(test_routes, '2025-08-11')
            
            if not formatted_message or len(formatted_message) < 10:
                raise ValueError("Сообщение не форматируется корректно")
            
            self.test_results['bot_functions'] = {
                'status': 'PASS',
                'details': f"Кнопок в клавиатуре: {buttons_count}, форматирование: OK"
            }
            self.log_test_result(test_name, 'PASS', f"Кнопок в клавиатуре: {buttons_count}, форматирование: OK")
            
        except Exception as e:
            self.test_results['bot_functions'] = {'status': 'ERROR', 'error': str(e)}
            self.log_test_result(test_name, 'ERROR', str(e))
    
    def test_auth_manager(self):
        """Тест менеджера авторизации"""
        test_name = "Auth Manager"
        self.log_test_start(test_name)
        
        try:
            from src.bot_auth_manager import bot_auth_manager
            
            # Тест базовых методов
            test_user_id = 999999
            
            # Проверяем, что пользователь не авторизован
            is_auth_before = bot_auth_manager.is_authenticated(test_user_id)
            
            # Тест создания сессии
            auth_session = bot_auth_manager._get_session_file(test_user_id)
            
            if not auth_session or not isinstance(auth_session, str):
                raise ValueError("Сессия не создается корректно")
            
            self.test_results['auth_manager'] = {
                'status': 'PASS',
                'details': f"Авторизация до теста: {is_auth_before}, сессия создана: OK"
            }
            self.log_test_result(test_name, 'PASS', f"Авторизация до теста: {is_auth_before}, сессия создана: OK")
            
        except Exception as e:
            self.test_results['auth_manager'] = {'status': 'ERROR', 'error': str(e)}
            self.log_test_result(test_name, 'ERROR', str(e))
    
    def test_admin_panel(self):
        """Тест админ-панели"""
        test_name = "Admin Panel"
        self.log_test_start(test_name)
        
        try:
            from src.admin_panel import AdminPanel
            
            # Создаем тестовую админ-панель
            test_admin_id = 123456789
            admin_panel = AdminPanel(test_admin_id)
            
            # Тест получения статистики мониторингов
            stats = admin_panel.get_monitoring_statistics({}, {})
            
            if not isinstance(stats, str) or len(stats) < 10:
                raise ValueError("Статистика не генерируется корректно")
            
            # Тест проверки прав администратора
            is_admin = admin_panel.is_admin(test_admin_id)
            is_not_admin = admin_panel.is_admin(999999)
            
            if not is_admin or is_not_admin:
                raise ValueError("Проверка прав администратора работает некорректно")
            
            # Тест создания клавиатуры
            keyboard = admin_panel.get_admin_menu_keyboard()
            
            if not keyboard or not hasattr(keyboard, 'inline_keyboard'):
                raise ValueError("Клавиатура админ-панели не создается")
            
            self.test_results['admin_panel'] = {
                'status': 'PASS',
                'details': f"Статистика: OK, права: OK, клавиатура: {len(keyboard.inline_keyboard)} кнопок"
            }
            self.log_test_result(test_name, 'PASS', f"Статистика: OK, права: OK, клавиатура: {len(keyboard.inline_keyboard)} кнопок")
            
        except Exception as e:
            self.test_results['admin_panel'] = {'status': 'ERROR', 'error': str(e)}
            self.log_test_result(test_name, 'ERROR', str(e))
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        print("🧪 ПОЛНОЕ ТЕСТИРОВАНИЕ БОТА MARHRUTOCHKATG")
        print("=" * 60)
        print(f"⏰ Время начала: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        # Запускаем все тесты
        test_methods = [
            self.test_environment,
            self.test_bot_imports,
            self.test_bot_functions,
            self.test_auth_manager,
            self.test_admin_panel,
            self.test_parser,  # Асинхронный тест в конце
        ]
        
        for test_method in test_methods[:-1]:  # Синхронные тесты
            try:
                test_method()
            except Exception as e:
                print(f"🔥 Критическая ошибка в тесте: {e}")
                traceback.print_exc()
        
        # Асинхронный тест парсера
        try:
            await self.test_parser()
        except Exception as e:
            print(f"🔥 Критическая ошибка в тесте парсера: {e}")
            traceback.print_exc()
        
        # Подводим итоги
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("")
        print("=" * 60)
        print("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        print("")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'PASS')
        failed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'FAIL')
        error_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'ERROR')
        
        for test_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            emoji = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '🔥'
            print(f"{emoji} {test_name.replace('_', ' ').title()}: {status}")
            
            if status in ['ERROR', 'FAIL']:
                error_msg = result.get('error', 'Неизвестная ошибка')
                print(f"   💬 {error_msg}")
            elif status == 'PASS' and 'details' in result:
                print(f"   💬 {result['details']}")
        
        print("")
        print(f"📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"   ✅ Успешно: {passed_tests}")
        print(f"   ❌ Провалено: {failed_tests}")
        print(f"   🔥 Ошибки: {error_tests}")
        print(f"   📈 Всего: {total_tests}")
        print(f"   ⏱️ Время выполнения: {duration.total_seconds():.2f} сек")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"   📊 Успешность: {success_rate:.1f}%")
        
        if passed_tests == total_tests:
            print("")
            print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
            print("✅ Бот готов к работе!")
            return 0
        else:
            print("")
            print("⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ!")
            if error_tests > 0:
                print("🔥 Есть критические ошибки - проверьте конфигурацию")
            if failed_tests > 0:
                print("❌ Некоторые функции работают неправильно")
            return 1

async def main():
    """Основная функция"""
    try:
        tester = CompleteBotTester()
        return await tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        return 1
    except Exception as e:
        print(f"\n🔥 Критическая ошибка: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Проверяем наличие .env файла
    if not os.path.exists('.env'):
        print("⚠️ Файл .env не найден!")
        print("💡 Создайте файл .env с необходимыми переменными")
        print("📝 Пример:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        print("ADMIN_TELEGRAM_ID=your_admin_id")
        sys.exit(1)
    
    # Загружаем переменные окружения
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️ python-dotenv не установлен")
        print("💡 Установите: pip install python-dotenv")
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
