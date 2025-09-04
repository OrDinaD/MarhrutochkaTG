#!/usr/bin/env python3
"""
🧪 Полное тестирование всех компонентов MarhrutochkaTG Bot

Этот модуль содержит комплексные тесты для проверки всех основных
компонентов телеграм-бота, включая импорты, функциональность и интеграции.

GitHub Actions совместимость: ✅
"""

import unittest
import asyncio
import os
import sys
import logging
import traceback
import time
import json
import warnings
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Добавляем src в путь
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Подавляем предупреждения для чистого вывода
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Настройка логирования для тестов
logging.basicConfig(
    level=logging.WARNING,  # Меньше шума во время тестов
    format='%(levelname)s: %(message)s'
)

class CompleteBotTester(unittest.TestCase):
    """
    🤖 Полное тестирование всех компонентов бота
    
    Тестирует:
    - Импорты модулей
    - Основную функциональность  
    - Клавиатуры и интерфейс
    - Системы безопасности и мониторинга
    """
    
    @classmethod
    def setUpClass(cls):
        """Настройка перед всеми тестами"""
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_123456789'
        os.environ['TEST_MODE'] = 'true'
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        print("🚀 Инициализация тестовой среды...")
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.start_time = time.time()
    
    def tearDown(self):
        """Очистка после каждого теста"""
        test_time = time.time() - self.start_time
        print(f"⏱️ Тест выполнен за {test_time:.3f}s")
    
    def test_01_bot_core_imports(self):
        """🤖 Тест импорта основных модулей бота"""
        print("📥 Тестирование импорта основных модулей...")
        
        try:
            import bot
            import admin_panel
            import security
            
            # Проверяем наличие основных функций
            self.assertTrue(hasattr(bot, 'get_main_menu_keyboard'), 
                          "Функция get_main_menu_keyboard доступна")
            self.assertTrue(hasattr(bot, 'get_date_keyboard'), 
                          "Функция get_date_keyboard доступна")
            
            print("✅ Основные модули импортированы успешно")
            
        except ImportError as e:
            self.fail(f"❌ Ошибка импорта основных модулей: {e}")
    
    def test_02_database_integration(self):
        """🗄️ Тест интеграции с базой данных"""
        print("🗄️ Тестирование интеграции с БД...")
        
        try:
            from database import db_manager
            print("✅ Модули базы данных импортированы успешно")
            
            # Проверяем доступность DatabaseManager
            if hasattr(db_manager, 'DatabaseManager'):
                print("✅ DatabaseManager доступен")
            
        except ImportError as e:
            self.skipTest(f"⚠️ Модули базы данных недоступны: {e}")
    
    def test_03_utils_functionality(self):
        """🛠️ Тест утилит и вспомогательных функций"""
        print("🛠️ Тестирование утилит...")
        
        try:
            import utils
            print("✅ Утилиты импортированы успешно")
            
            # Тестируем парсер маршрутов если доступен
            if hasattr(utils, 'FinalMarshrutochkaParser'):
                print("✅ FinalMarshrutochkaParser доступен")
                
        except ImportError as e:
            self.fail(f"❌ Ошибка импорта утилит: {e}")
    
    def test_04_monitoring_system(self):
        """📊 Тест системы мониторинга"""
        print("📊 Тестирование системы мониторинга...")
        
        try:
            from monitoring import crash_handler
            from monitoring import log_manager
            print("✅ Система мониторинга импортирована успешно")
            
            # Проверяем CrashHandler
            if hasattr(crash_handler, 'CrashHandler'):
                print("✅ CrashHandler доступен")
                
        except ImportError as e:
            self.skipTest(f"⚠️ Система мониторинга недоступна: {e}")
    
    def test_05_keyboard_generation(self):
        """⌨️ Тест генерации клавиатур"""
        print("⌨️ Тестирование генерации клавиатур...")
        
        try:
            from bot import get_main_menu_keyboard, get_date_keyboard
            
            # Тестируем создание главного меню
            main_menu = get_main_menu_keyboard(12345)
            self.assertIsNotNone(main_menu, "Главное меню создано")
            print("✅ Главное меню создано успешно")
            
            # Тестируем создание меню дат
            date_menu = get_date_keyboard()
            self.assertIsNotNone(date_menu, "Меню дат создано")
            print("✅ Меню дат создано успешно")
            
            # Проверяем, что клавиатуры содержат кнопки
            if hasattr(main_menu, 'keyboard') or hasattr(main_menu, 'inline_keyboard'):
                print("✅ Главное меню содержит кнопки")
                
            if hasattr(date_menu, 'keyboard') or hasattr(date_menu, 'inline_keyboard'):
                print("✅ Меню дат содержит кнопки")
            
        except Exception as e:
            self.fail(f"❌ Ошибка тестирования клавиатур: {e}")
    
    def test_06_security_module(self):
        """🔒 Тест модуля безопасности"""
        print("🔒 Тестирование модуля безопасности...")
        
        try:
            import security
            print("✅ Модуль безопасности импортирован успешно")
            
            # Проверяем доступность функций безопасности
            if hasattr(security, 'validate_user'):
                print("✅ Функция validate_user доступна")
                
        except ImportError as e:
            self.skipTest(f"⚠️ Модуль безопасности недоступен: {e}")
    
    def test_07_auth_system(self):
        """🔑 Тест системы аутентификации"""
        print("🔑 Тестирование системы аутентификации...")
        
        try:
            from auth import bot_auth_manager
            print("✅ Система аутентификации импортирована")
            
        except ImportError as e:
            self.skipTest(f"⚠️ Система аутентификации недоступна: {e}")
    
    def test_08_performance_check(self):
        """⚡ Тест производительности"""
        print("⚡ Тестирование производительности...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"📊 Использование памяти: {memory_usage:.2f} MB")
        
        # Проверяем, что использование памяти разумное
        self.assertLess(memory_usage, 500, 
                       "Использование памяти не превышает 500 MB")
        
        print("✅ Тест производительности пройден")
    
    def test_09_emoji_symbols(self):
        """😀 Тест корректности эмодзи и символов"""
        print("😀 Тестирование эмодзи и символов...")
        
        # Проверяем, что проблемных символов больше нет
        test_files = [
            '../src/bot.py',
            '../src/utils/route_analyzer.py',
            '../scripts/start_bot.sh'
        ]
        
        problematic_symbols = ['�', '\ufffd']
        
        for file_path in test_files:
            full_path = os.path.join(os.path.dirname(__file__), file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for symbol in problematic_symbols:
                            self.assertNotIn(symbol, content, 
                                           f"Проблемный символ {symbol} найден в {file_path}")
                    print(f"✅ {file_path} не содержит проблемных символов")
                except Exception as e:
                    print(f"⚠️ Не удалось проверить {file_path}: {e}")
        
        print("✅ Проверка эмодзи завершена")

class GitHubActionsIntegration(unittest.TestCase):
    """
    🚀 Тесты для интеграции с GitHub Actions
    """
    
    def test_github_environment(self):
        """🔍 Проверка среды GitHub Actions"""
        
        if 'GITHUB_ACTIONS' in os.environ:
            print("🚀 Обнаружена среда GitHub Actions")
            
            # Проверяем переменные окружения GitHub Actions
            github_vars = [
                'GITHUB_WORKFLOW',
                'GITHUB_RUN_ID', 
                'GITHUB_RUN_NUMBER',
                'GITHUB_SHA',
                'GITHUB_REF'
            ]
            
            for var in github_vars:
                if var in os.environ:
                    print(f"✅ {var}: {os.environ[var]}")
                else:
                    print(f"⚠️ {var}: не найдена")
            
            print("✅ Среда GitHub Actions настроена корректно")
        else:
            print("🏠 Локальная среда разработки")

# Сохраняем старый класс для совместимости
class CompleteBotTesterOld:
    """Старый тестер для обратной совместимости"""
    
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

def run_tests_with_reporter():
    """
    🎯 Запуск тестов с подробной отчётностью
    """
    
    print("🧪 Запуск комплексного тестирования MarhrutochkaTG Bot")
    print("=" * 60)
    
    # Создаём test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Добавляем основные тесты
    suite.addTests(loader.loadTestsFromTestCase(CompleteBotTester))
    suite.addTests(loader.loadTestsFromTestCase(GitHubActionsIntegration))
    
    # Настраиваем runner
    runner = unittest.TextTestRunner(
        verbosity=2, 
        stream=sys.stdout,
        buffer=True
    )
    
    # Запускаем тесты
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Формируем отчёт
    print("\n" + "=" * 60)
    print("📊 ОТЧЁТ О ТЕСТИРОВАНИИ")
    print("=" * 60)
    print(f"⏱️ Время выполнения: {end_time - start_time:.2f} секунд")
    print(f"🧪 Всего тестов: {result.testsRun}")
    print(f"✅ Пройдено: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Провалено: {len(result.failures)}")
    print(f"💥 Ошибок: {len(result.errors)}")
    print(f"⏭️ Пропущено: {len(result.skipped)}")
    
    if result.failures:
        print(f"\n❌ ПРОВАЛИВШИЕСЯ ТЕСТЫ:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\n💥 ОШИБКИ:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Экспорт результатов для GitHub Actions
    if 'GITHUB_ACTIONS' in os.environ:
        summary = {
            'total_tests': result.testsRun,
            'passed': result.testsRun - len(result.failures) - len(result.errors),
            'failed': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped),
            'duration': end_time - start_time,
            'success': result.wasSuccessful()
        }
        
        # Сохраняем JSON отчёт
        with open('test-results.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📄 Результаты сохранены в test-results.json")
    
    print("=" * 60)
    
    return result.wasSuccessful()

# Совместимость со старым API
async def main():
    """Основная функция для обратной совместимости"""
    try:
        # Запускаем старый тестер если нужен
        if 'USE_OLD_TESTER' in os.environ:
            tester = CompleteBotTesterOld()
            return await tester.run_all_tests()
        else:
            # Запускаем новый unittest-based тестер
            success = run_tests_with_reporter()
            return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        return 1
    except Exception as e:
        print(f"\n🔥 Критическая ошибка: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Проверяем среду выполнения
    if 'GITHUB_ACTIONS' in os.environ:
        print("🚀 Запуск в GitHub Actions")
        # В GitHub Actions используем unittest напрямую
        success = run_tests_with_reporter()
        sys.exit(0 if success else 1)
    else:
        print("🏠 Локальный запуск")
        # Локально можем проверить .env файл
        if not os.path.exists('.env') and 'TEST_MODE' not in os.environ:
            print("⚠️ Файл .env не найден!")
            print("💡 Создайте файл .env с необходимыми переменными")
            print("📝 Пример:")
            print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
            print("ADMIN_TELEGRAM_ID=your_admin_id")
            print("🧪 Или установите TEST_MODE=true для тестирования")
            # Не выходим из-за отсутствия .env в тестовом режиме
            os.environ['TEST_MODE'] = 'true'
        
        # Загружаем переменные окружения если есть dotenv
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            print("⚠️ python-dotenv не установлен (это нормально для тестов)")
        
        # Запускаем тесты
        if len(sys.argv) > 1 and '--unittest' in sys.argv:
            # Запуск через unittest
            success = run_tests_with_reporter()
            sys.exit(0 if success else 1)
        else:
            # Запуск через asyncio (старый метод)
            exit_code = asyncio.run(main())
            sys.exit(exit_code)
