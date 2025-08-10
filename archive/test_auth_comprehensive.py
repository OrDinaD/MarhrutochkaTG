#!/usr/bin/env python3
"""
Тест системы авторизации с предоставленными учетными данными
"""

import asyncio
import logging
import json
import sys
import os
from datetime import datetime

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from improved_auth import ImprovedAuthManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auth_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AuthTester:
    """Класс для тестирования системы авторизации"""
    
    def __init__(self):
        self.test_phone = "+375299605390"
        self.test_password = "Zxcvbnm,1"
        self.results = {}
    
    async def run_comprehensive_test(self):
        """Запуск полного теста авторизации"""
        logger.info("🚀 Начинаем полное тестирование системы авторизации")
        logger.info(f"📱 Тестовый номер: {self.test_phone}")
        logger.info(f"🔐 Тестовый пароль: {'*' * len(self.test_password)}")
        
        # Тест 1: Проверка валидации данных
        await self._test_data_validation()
        
        # Тест 2: Попытка входа через requests
        await self._test_requests_login()
        
        # Тест 3: Попытка входа через Playwright (если доступен)
        await self._test_playwright_login()
        
        # Тест 4: Сравнение результатов
        await self._compare_results()
        
        # Сохранение результатов
        await self._save_results()
        
        return self.results
    
    async def _test_data_validation(self):
        """Тест валидации входных данных"""
        logger.info("\n🔍 Тест 1: Валидация входных данных")
        
        try:
            auth_manager = ImprovedAuthManager()
            
            # Проверка номера телефона
            phone_valid, phone_msg = auth_manager.validate_phone_number(self.test_phone)
            logger.info(f"📱 Валидация номера: {'✅' if phone_valid else '❌'} - {phone_msg}")
            
            # Проверка пароля
            password_valid, password_msg = auth_manager.validate_password(self.test_password)
            logger.info(f"🔐 Валидация пароля: {'✅' if password_valid else '❌'} - {password_msg}")
            
            self.results['validation'] = {
                'phone_valid': phone_valid,
                'phone_message': phone_msg,
                'password_valid': password_valid,
                'password_message': password_msg,
                'overall_valid': phone_valid and password_valid
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации: {e}")
            self.results['validation'] = {
                'error': str(e),
                'overall_valid': False
            }
    
    async def _test_requests_login(self):
        """Тест входа через requests"""
        logger.info("\n🌐 Тест 2: Вход через requests")
        
        try:
            auth_manager = ImprovedAuthManager()
            
            # Попытка входа
            login_start = datetime.now()
            login_success = auth_manager.login(self.test_phone, self.test_password)
            login_end = datetime.now()
            login_duration = (login_end - login_start).total_seconds()
            
            logger.info(f"🔐 Результат входа: {'✅ Успешно' if login_success else '❌ Неудачно'}")
            logger.info(f"⏱️ Время выполнения: {login_duration:.2f} сек")
            
            # Проверка аутентификации
            is_authenticated = auth_manager.is_authenticated
            logger.info(f"🔓 Статус аутентификации: {'✅' if is_authenticated else '❌'}")
            
            # Получение профиля
            profile_result = auth_manager.get_profile()
            logger.info(f"👤 Получение профиля: {'✅' if profile_result['success'] else '❌'}")
            
            if profile_result['success']:
                profile_data = profile_result['data']
                logger.info(f"📞 Телефон в профиле: {profile_data.get('phone', 'не найден')}")
                logger.info(f"👤 Имя в профиле: {profile_data.get('name', 'не найдено')}")
                logger.info(f"📧 Email в профиле: {profile_data.get('email', 'не найден')}")
                logger.info(f"💰 Баланс: {profile_data.get('balance', 'не найден')}")
            
            # Получение билетов
            tickets = auth_manager.get_tickets()
            logger.info(f"🎫 Найдено билетов: {len(tickets)}")
            
            self.results['requests_login'] = {
                'login_success': login_success,
                'login_duration': login_duration,
                'is_authenticated': is_authenticated,
                'profile_success': profile_result['success'],
                'profile_data': profile_result.get('data', {}),
                'tickets_count': len(tickets),
                'tickets': tickets[:5]  # Первые 5 билетов
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка requests входа: {e}")
            self.results['requests_login'] = {
                'error': str(e),
                'login_success': False
            }
    
    async def _test_playwright_login(self):
        """Тест входа через Playwright"""
        logger.info("\n🎭 Тест 3: Вход через Playwright")
        
        try:
            auth_manager = ImprovedAuthManager()
            
            # Проверяем доступность Playwright
            try:
                from playwright.async_api import async_playwright
                playwright_available = True
                logger.info("✅ Playwright доступен")
            except ImportError:
                playwright_available = False
                logger.warning("⚠️ Playwright не установлен")
                self.results['playwright_login'] = {
                    'available': False,
                    'error': 'Playwright не установлен'
                }
                return
            
            # Запуск теста с Playwright
            login_start = datetime.now()
            playwright_result = await auth_manager.test_login_with_playwright(
                self.test_phone, 
                self.test_password
            )
            login_end = datetime.now()
            login_duration = (login_end - login_start).total_seconds()
            
            logger.info(f"🎭 Результат Playwright: {'✅' if playwright_result['success'] else '❌'}")
            logger.info(f"⏱️ Время выполнения: {login_duration:.2f} сек")
            
            if playwright_result['success']:
                profile_data = playwright_result.get('profile_data', {})
                logger.info(f"🔗 URL после входа: {playwright_result.get('url', 'не определен')}")
                logger.info(f"👤 Данные профиля: {len(profile_data)} полей")
                
                for key, value in profile_data.items():
                    logger.info(f"  📋 {key}: {value}")
            else:
                logger.error(f"❌ Ошибка Playwright: {playwright_result.get('error', 'неизвестная ошибка')}")
            
            self.results['playwright_login'] = {
                'available': playwright_available,
                'success': playwright_result['success'],
                'duration': login_duration,
                'profile_data': playwright_result.get('profile_data', {}),
                'url': playwright_result.get('url', ''),
                'error': playwright_result.get('error', '')
            }
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка Playwright: {e}")
            self.results['playwright_login'] = {
                'available': False,
                'error': str(e),
                'success': False
            }
    
    async def _compare_results(self):
        """Сравнение результатов разных методов"""
        logger.info("\n📊 Тест 4: Сравнение результатов")
        
        requests_success = self.results.get('requests_login', {}).get('login_success', False)
        playwright_success = self.results.get('playwright_login', {}).get('success', False)
        
        logger.info(f"🌐 Requests login: {'✅' if requests_success else '❌'}")
        logger.info(f"🎭 Playwright login: {'✅' if playwright_success else '❌'}")
        
        if requests_success and playwright_success:
            logger.info("🎉 Оба метода успешны! Авторизация работает корректно.")
            
            # Сравниваем данные профиля
            requests_profile = self.results.get('requests_login', {}).get('profile_data', {})
            playwright_profile = self.results.get('playwright_login', {}).get('profile_data', {})
            
            common_fields = set(requests_profile.keys()) & set(playwright_profile.keys())
            if common_fields:
                logger.info(f"🔍 Общих полей профиля: {len(common_fields)}")
                for field in common_fields:
                    req_value = requests_profile[field]
                    pw_value = playwright_profile[field]
                    match = req_value == pw_value
                    logger.info(f"  📋 {field}: {'✅' if match else '❌'} (requests: {req_value}, playwright: {pw_value})")
        
        elif requests_success:
            logger.info("⚠️ Только requests метод успешен")
        elif playwright_success:
            logger.info("⚠️ Только Playwright метод успешен")
        else:
            logger.error("❌ Оба метода неуспешны - требуется доработка!")
        
        self.results['comparison'] = {
            'requests_success': requests_success,
            'playwright_success': playwright_success,
            'both_successful': requests_success and playwright_success,
            'any_successful': requests_success or playwright_success
        }
    
    async def _save_results(self):
        """Сохранение результатов в файл"""
        try:
            results_file = f'auth_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"💾 Результаты сохранены в {results_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения результатов: {e}")
    
    def print_summary(self):
        """Печать краткого отчета"""
        logger.info("\n" + "="*60)
        logger.info("📋 КРАТКИЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        logger.info("="*60)
        
        # Валидация
        validation = self.results.get('validation', {})
        logger.info(f"🔍 Валидация данных: {'✅' if validation.get('overall_valid') else '❌'}")
        
        # Requests
        requests_result = self.results.get('requests_login', {})
        logger.info(f"🌐 Requests вход: {'✅' if requests_result.get('login_success') else '❌'}")
        if requests_result.get('login_success'):
            logger.info(f"  👤 Профиль: {'✅' if requests_result.get('profile_success') else '❌'}")
            logger.info(f"  🎫 Билетов: {requests_result.get('tickets_count', 0)}")
        
        # Playwright
        playwright_result = self.results.get('playwright_login', {})
        if playwright_result.get('available'):
            logger.info(f"🎭 Playwright вход: {'✅' if playwright_result.get('success') else '❌'}")
            if playwright_result.get('success'):
                profile_count = len(playwright_result.get('profile_data', {}))
                logger.info(f"  👤 Полей профиля: {profile_count}")
        else:
            logger.info("🎭 Playwright: не доступен")
        
        # Общий результат
        comparison = self.results.get('comparison', {})
        if comparison.get('any_successful'):
            logger.info("🎉 ОБЩИЙ РЕЗУЛЬТАТ: УСПЕШНО")
            if comparison.get('both_successful'):
                logger.info("✨ Оба метода работают корректно")
            else:
                logger.info("⚠️ Работает только один метод")
        else:
            logger.info("❌ ОБЩИЙ РЕЗУЛЬТАТ: НЕУДАЧНО")
            logger.info("🔧 Требуется доработка системы авторизации")
        
        logger.info("="*60)


async def main():
    """Главная функция"""
    try:
        logger.info("🚀 Запуск тестирования системы авторизации")
        
        tester = AuthTester()
        results = await tester.run_comprehensive_test()
        
        # Печатаем краткий отчет
        tester.print_summary()
        
        return results
        
    except KeyboardInterrupt:
        logger.info("⏹️ Тестирование прервано пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    # Запускаем тест
    results = asyncio.run(main())
