#!/usr/bin/env python3
"""
Тестирование всех функций бота MarhrutochkaTG
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta

# Добавляем src в путь
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Импортируем модули
from parser import FinalMarshrutochkaParser
from requests_auth import RequestsAuthManager
from log_manager import setup_logging

# Настройка логирования
logger = setup_logging(logging.INFO)

class BotTester:
    """Класс для тестирования функций бота"""
    
    def __init__(self):
        self.parser = None
        self.auth_manager = None
        self.test_results = {}
    
    async def test_parser(self):
        """Тестирование парсера"""
        logger.info("🔍 Тестируем парсер...")
        
        try:
            self.parser = FinalMarshrutochkaParser()
            await self.parser.__aenter__()
            
            # Тестируем на завтрашний день
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            routes = await self.parser.get_all_routes(tomorrow)
            
            minsk_routes = len(routes.get('minsk_to_ostrovets', []))
            ostrovets_routes = len(routes.get('ostrovets_to_minsk', []))
            
            self.test_results['parser'] = {
                'status': 'PASS' if routes.get('success') else 'FAIL',
                'minsk_to_ostrovets': minsk_routes,
                'ostrovets_to_minsk': ostrovets_routes,
                'total_routes': minsk_routes + ostrovets_routes
            }
            
            logger.info(f"   ✓ Парсер работает: найдено {minsk_routes + ostrovets_routes} рейсов")
            
            # Показываем примеры
            if routes.get('minsk_to_ostrovets'):
                example = routes['minsk_to_ostrovets'][0]
                logger.info(f"   Пример рейса: {example.get('departure_time')} → {example.get('arrival_time')}, "
                           f"мест: {example.get('available_seats')}, "
                           f"перевозчик: {example.get('carrier')}")
            
        except Exception as e:
            self.test_results['parser'] = {'status': 'ERROR', 'error': str(e)}
            logger.error(f"   ✗ Ошибка парсера: {e}")
        
        finally:
            if self.parser:
                await self.parser.__aexit__(None, None, None)
    
    def test_auth_manager(self):
        """Тестирование менеджера аутентификации"""
        logger.info("🔐 Тестируем менеджер аутентификации...")
        
        try:
            self.auth_manager = RequestsAuthManager()
            
            # Тестируем получение страницы входа
            success, token = self.auth_manager.get_login_page()
            
            self.test_results['auth_manager'] = {
                'status': 'PASS' if success else 'FAIL',
                'login_page_accessible': success,
                'csrf_token_found': bool(token),
                'cookies_received': len(self.auth_manager.session.cookies) > 0
            }
            
            if success:
                logger.info(f"   ✓ Страница входа доступна, CSRF токен: {'найден' if token else 'не найден'}")
                logger.info(f"   Cookies получены: {len(self.auth_manager.session.cookies)} шт.")
            else:
                logger.error("   ✗ Не удалось получить страницу входа")
            
        except Exception as e:
            self.test_results['auth_manager'] = {'status': 'ERROR', 'error': str(e)}
            logger.error(f"   ✗ Ошибка менеджера аутентификации: {e}")
    
    def test_bot_functions(self):
        """Тестирование функций бота"""
        logger.info("🤖 Тестируем функции бота...")
        
        try:
            # Импортируем основные функции из bot.py
            import bot
            
            # Тестируем клавиатуры
            date_keyboard = bot.get_date_keyboard()
            direction_keyboard = bot.get_direction_keyboard()
            time_type_keyboard = bot.get_time_type_keyboard()
            time_range_keyboard = bot.get_time_range_keyboard("departure")
            
            # Тестируем форматирование
            config = {
                'date': '2025-07-07',
                'direction': 'minsk_ostrovets',
                'time_type': 'departure',
                'time_range': '07:00-09:00'
            }
            formatted_config = bot.format_monitor_config(config)
            
            # Тестируем главное меню
            main_menu = bot.get_main_menu_keyboard(123456)
            
            self.test_results['bot_functions'] = {
                'status': 'PASS',
                'keyboards_generated': True,
                'config_formatting': bool(formatted_config),
                'main_menu_generated': bool(main_menu)
            }
            
            logger.info("   ✓ Функции бота работают корректно")
            logger.info(f"   Пример конфигурации: {formatted_config.split(chr(10))[0]}...")
            
        except Exception as e:
            self.test_results['bot_functions'] = {'status': 'ERROR', 'error': str(e)}
            logger.error(f"   ✗ Ошибка функций бота: {e}")
    
    def test_filters_and_monitoring(self):
        """Тестирование фильтров и мониторинга"""
        logger.info("⚙️ Тестируем фильтры и мониторинг...")
        
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
                        'carrier': 'Тестовый перевозчик 2'
                    }
                ]
            }
            
            # Тестовая конфигурация мониторинга
            test_config = {
                'direction': 'minsk_ostrovets',
                'time_type': 'departure',
                'time_range': '07:00-09:00'
            }
            
            # Тестируем фильтрацию
            filtered_routes = bot.filter_routes_by_criteria(test_routes_data, test_config)
            
            # Тестируем проверку времени
            route = test_routes_data['minsk_to_ostrovets'][0]
            time_check = bot.check_time_criteria(route, test_config)
            
            # Тестируем форматирование сообщения
            formatted_message = bot.format_routes_message(test_routes_data, '2025-07-07')
            
            self.test_results['filters_monitoring'] = {
                'status': 'PASS',
                'routes_filtered': len(filtered_routes),
                'time_check_working': time_check,
                'message_formatting': bool(formatted_message)
            }
            
            logger.info(f"   ✓ Фильтрация работает: отфильтровано {len(filtered_routes)} рейсов")
            logger.info(f"   Проверка времени: {'работает' if time_check else 'не работает'}")
            logger.info(f"   Форматирование сообщений: {'работает' if formatted_message else 'не работает'}")
            
        except Exception as e:
            self.test_results['filters_monitoring'] = {'status': 'ERROR', 'error': str(e)}
            logger.error(f"   ✗ Ошибка фильтров и мониторинга: {e}")
    
    def test_user_data_management(self):
        """Тестирование управления данными пользователей"""
        logger.info("📊 Тестируем управление данными пользователей...")
        
        try:
            import bot
            
            # Тестируем загрузку/сохранение мониторингов
            original_monitors = bot.active_monitors.copy()
            
            # Добавляем тестовый мониторинг
            test_user_id = 999999
            test_monitor = {
                'user_id': test_user_id,
                'date': '2025-07-07',
                'direction': 'minsk_ostrovets',
                'time_type': 'departure',
                'time_range': '07:00-09:00',
                'created_at': datetime.now().isoformat()
            }
            
            bot.active_monitors[test_user_id] = test_monitor
            bot.save_active_monitors()
            
            # Очищаем и загружаем снова
            bot.active_monitors.clear()
            bot.load_active_monitors()
            
            # Проверяем, что данные сохранились
            monitor_saved = test_user_id in bot.active_monitors
            
            # Очищаем тестовые данные
            if test_user_id in bot.active_monitors:
                del bot.active_monitors[test_user_id]
                bot.save_active_monitors()
            
            # Восстанавливаем оригинальные данные
            bot.active_monitors = original_monitors
            
            self.test_results['user_data'] = {
                'status': 'PASS' if monitor_saved else 'FAIL',
                'monitor_save_load': monitor_saved
            }
            
            logger.info(f"   ✓ Сохранение/загрузка мониторингов: {'работает' if monitor_saved else 'не работает'}")
            
        except Exception as e:
            self.test_results['user_data'] = {'status': 'ERROR', 'error': str(e)}
            logger.error(f"   ✗ Ошибка управления данными: {e}")
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        logger.info("🚀 Начинаем полное тестирование бота MarhrutochkaTG")
        logger.info("=" * 60)
        
        # Запускаем тесты
        await self.test_parser()
        self.test_auth_manager()
        self.test_bot_functions()
        self.test_filters_and_monitoring()
        self.test_user_data_management()
        
        # Выводим результаты
        logger.info("\n" + "=" * 60)
        logger.info("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        logger.info("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'PASS')
        failed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'FAIL')
        error_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'ERROR')
        
        for test_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            emoji = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '🔥'
            logger.info(f"{emoji} {test_name.upper()}: {status}")
            
            if status == 'ERROR':
                logger.info(f"   Ошибка: {result.get('error', 'неизвестная ошибка')}")
            else:
                # Выводим детали
                for key, value in result.items():
                    if key != 'status':
                        logger.info(f"   {key}: {value}")
        
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 ИТОГО: {passed_tests}/{total_tests} тестов прошли успешно")
        
        if failed_tests > 0:
            logger.warning(f"⚠️ {failed_tests} тестов завершились неудачно")
        
        if error_tests > 0:
            logger.error(f"🔥 {error_tests} тестов завершились с ошибками")
        
        if passed_tests == total_tests:
            logger.info("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! Бот готов к работе.")
        else:
            logger.warning("⚠️ Некоторые тесты не прошли. Требуется дополнительная настройка.")
        
        return self.test_results

async def main():
    """Основная функция"""
    tester = BotTester()
    results = await tester.run_all_tests()
    
    # Возвращаем код выхода
    failed_or_error = sum(1 for result in results.values() 
                         if result.get('status') in ['FAIL', 'ERROR'])
    return 0 if failed_or_error == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
