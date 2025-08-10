#!/usr/bin/env python3
"""
Финальный тест системы авторизации с исправленным менеджером
"""

import asyncio
import logging
import json
import sys
import os
from datetime import datetime

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fixed_auth import FixedAuthManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('final_auth_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class FinalAuthTester:
    """Финальный класс для тестирования системы авторизации"""
    
    def __init__(self):
        self.test_phone = "+375299605390"
        self.test_password = "Zxcvbnm,1"
        self.results = {}
    
    async def run_final_test(self):
        """Запуск финального теста авторизации"""
        logger.info("🚀 Запуск финального теста системы авторизации")
        logger.info(f"📱 Тестовый номер: {self.test_phone}")
        logger.info(f"🔐 Тестовый пароль: {'*' * len(self.test_password)}")
        
        # Тест 1: Создание менеджера и поиск URL
        logger.info("\n🔍 Тест 1: Инициализация менеджера")
        auth_manager = FixedAuthManager()
        
        if auth_manager.base_url:
            logger.info(f"✅ Найден рабочий URL: {auth_manager.base_url}")
            self.results['url_found'] = True
            self.results['base_url'] = auth_manager.base_url
        else:
            logger.error("❌ Рабочий URL не найден")
            self.results['url_found'] = False
            return self.results
        
        # Тест 2: Валидация данных
        logger.info("\n🔍 Тест 2: Валидация входных данных")
        phone_valid, phone_msg = auth_manager.validate_phone_number(self.test_phone)
        password_valid, password_msg = auth_manager.validate_password(self.test_password)
        
        logger.info(f"📱 Валидация номера: {'✅' if phone_valid else '❌'} - {phone_msg}")
        logger.info(f"🔐 Валидация пароля: {'✅' if password_valid else '❌'} - {password_msg}")
        
        self.results['validation'] = {
            'phone_valid': phone_valid,
            'phone_message': phone_msg,
            'password_valid': password_valid,
            'password_message': password_msg,
            'overall_valid': phone_valid and password_valid
        }
        
        if not (phone_valid and password_valid):
            logger.error("❌ Валидация не пройдена, прекращаем тест")
            return self.results
        
        # Тест 3: Playwright тест (сначала, чтобы получить отладочную информацию)
        logger.info("\n🎭 Тест 3: Тестирование с Playwright")
        try:
            playwright_start = datetime.now()
            playwright_result = await auth_manager.test_with_playwright(self.test_phone, self.test_password)
            playwright_end = datetime.now()
            playwright_duration = (playwright_end - playwright_start).total_seconds()
            
            logger.info(f"🎭 Результат Playwright: {'✅' if playwright_result['success'] else '❌'}")
            logger.info(f"⏱️ Время выполнения: {playwright_duration:.2f} сек")
            
            if playwright_result['success']:
                profile_data = playwright_result.get('profile_data', {})
                logger.info(f"🔗 URL после входа: {playwright_result.get('url', 'не определен')}")
                logger.info(f"👤 Найдено полей профиля: {len(profile_data)}")
                
                for key, value in profile_data.items():
                    logger.info(f"  📋 {key}: {value}")
            else:
                logger.error(f"❌ Ошибка Playwright: {playwright_result.get('error', 'неизвестная ошибка')}")
            
            self.results['playwright'] = {
                'success': playwright_result['success'],
                'duration': playwright_duration,
                'profile_data': playwright_result.get('profile_data', {}),
                'url': playwright_result.get('url', ''),
                'error': playwright_result.get('error', '')
            }
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка Playwright: {e}")
            self.results['playwright'] = {
                'success': False,
                'error': str(e)
            }
        
        # Тест 4: Requests тест
        logger.info("\n🌐 Тест 4: Тестирование с requests")
        try:
            requests_start = datetime.now()
            login_success = auth_manager.login(self.test_phone, self.test_password)
            requests_end = datetime.now()
            requests_duration = (requests_end - requests_start).total_seconds()
            
            logger.info(f"🔐 Результат входа: {'✅ Успешно' if login_success else '❌ Неудачно'}")
            logger.info(f"⏱️ Время выполнения: {requests_duration:.2f} сек")
            
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
                logger.info(f"🔧 Источник данных: {profile_data.get('source', 'неизвестно')}")
            
            # Получение билетов
            tickets = auth_manager.get_tickets()
            logger.info(f"🎫 Найдено билетов: {len(tickets)}")
            
            self.results['requests'] = {
                'login_success': login_success,
                'duration': requests_duration,
                'is_authenticated': is_authenticated,
                'profile_success': profile_result['success'],
                'profile_data': profile_result.get('data', {}),
                'tickets_count': len(tickets),
                'tickets': tickets[:3]  # Первые 3 билета
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка requests тестирования: {e}")
            self.results['requests'] = {
                'login_success': False,
                'error': str(e)
            }
        
        # Тест 5: Анализ результатов
        await self._analyze_results()
        
        # Сохранение результатов
        await self._save_results()
        
        return self.results
    
    async def _analyze_results(self):
        """Анализ результатов тестирования"""
        logger.info("\n📊 Тест 5: Анализ результатов")
        
        playwright_success = self.results.get('playwright', {}).get('success', False)
        requests_success = self.results.get('requests', {}).get('login_success', False)
        
        logger.info(f"🎭 Playwright: {'✅' if playwright_success else '❌'}")
        logger.info(f"🌐 Requests: {'✅' if requests_success else '❌'}")
        
        # Анализ ошибок
        if not playwright_success:
            pw_error = self.results.get('playwright', {}).get('error', '')
            logger.error(f"🎭 Ошибка Playwright: {pw_error}")
        
        if not requests_success:
            req_error = self.results.get('requests', {}).get('error', '')
            logger.error(f"🌐 Ошибка Requests: {req_error}")
        
        # Общий анализ
        if playwright_success and requests_success:
            logger.info("🎉 ОБА МЕТОДА УСПЕШНЫ! Система авторизации работает корректно.")
            recommendation = "success"
        elif playwright_success or requests_success:
            successful_method = "Playwright" if playwright_success else "Requests"
            logger.info(f"⚠️ ЧАСТИЧНЫЙ УСПЕХ: работает только {successful_method}")
            recommendation = "partial"
        else:
            logger.error("❌ ПРОВАЛ: оба метода неуспешны")
            recommendation = "failure"
        
        # Рекомендации
        logger.info("\n💡 РЕКОМЕНДАЦИИ:")
        
        if recommendation == "success":
            logger.info("✅ Система авторизации готова к использованию")
            logger.info("✅ Можно интегрировать в основной бот")
            logger.info("✅ Рекомендуется использовать requests для продакшена")
        elif recommendation == "partial":
            if playwright_success:
                logger.info("⚠️ Используйте Playwright для критически важных операций")
                logger.info("⚠️ Исследуйте проблемы с requests методом")
            else:
                logger.info("⚠️ Используйте requests для продакшена")
                logger.info("⚠️ Playwright можно использовать для отладки")
        else:
            logger.info("❌ Требуется дополнительная отладка")
            logger.info("❌ Проверьте правильность учетных данных")
            logger.info("❌ Возможно, сайт изменил структуру")
        
        self.results['analysis'] = {
            'playwright_success': playwright_success,
            'requests_success': requests_success,
            'recommendation': recommendation,
            'overall_success': playwright_success or requests_success
        }
    
    async def _save_results(self):
        """Сохранение результатов в файл"""
        try:
            results_file = f'final_auth_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"💾 Результаты сохранены в {results_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения результатов: {e}")
    
    def print_final_summary(self):
        """Печать финального отчета"""
        logger.info("\n" + "="*70)
        logger.info("📋 ФИНАЛЬНЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ СИСТЕМЫ АВТОРИЗАЦИИ")
        logger.info("="*70)
        
        # URL
        if self.results.get('url_found'):
            logger.info(f"🌐 Рабочий URL: {self.results.get('base_url')}")
        else:
            logger.info("❌ Рабочий URL не найден")
        
        # Валидация
        validation = self.results.get('validation', {})
        logger.info(f"🔍 Валидация данных: {'✅' if validation.get('overall_valid') else '❌'}")
        
        # Результаты тестов
        playwright_result = self.results.get('playwright', {})
        requests_result = self.results.get('requests', {})
        
        logger.info(f"🎭 Playwright тест: {'✅' if playwright_result.get('success') else '❌'}")
        if playwright_result.get('success'):
            profile_count = len(playwright_result.get('profile_data', {}))
            logger.info(f"  👤 Полей профиля: {profile_count}")
            logger.info(f"  ⏱️ Время: {playwright_result.get('duration', 0):.2f}с")
        
        logger.info(f"🌐 Requests тест: {'✅' if requests_result.get('login_success') else '❌'}")
        if requests_result.get('login_success'):
            logger.info(f"  👤 Профиль: {'✅' if requests_result.get('profile_success') else '❌'}")
            logger.info(f"  🎫 Билетов: {requests_result.get('tickets_count', 0)}")
            logger.info(f"  ⏱️ Время: {requests_result.get('duration', 0):.2f}с")
        
        # Общий результат
        analysis = self.results.get('analysis', {})
        recommendation = analysis.get('recommendation', 'unknown')
        
        if recommendation == "success":
            logger.info("🎉 ОБЩИЙ РЕЗУЛЬТАТ: ПОЛНЫЙ УСПЕХ")
            logger.info("✨ Система авторизации полностью функциональна")
        elif recommendation == "partial":
            logger.info("⚠️ ОБЩИЙ РЕЗУЛЬТАТ: ЧАСТИЧНЫЙ УСПЕХ")
            logger.info("🔧 Один из методов работает корректно")
        else:
            logger.info("❌ ОБЩИЙ РЕЗУЛЬТАТ: ТРЕБУЕТСЯ ДОРАБОТКА")
            logger.info("🛠️ Необходимо исследовать причины сбоев")
        
        logger.info("="*70)


async def main():
    """Главная функция"""
    try:
        logger.info("🚀 Запуск финального тестирования системы авторизации")
        
        tester = FinalAuthTester()
        results = await tester.run_final_test()
        
        # Печатаем финальный отчет
        tester.print_final_summary()
        
        return results
        
    except KeyboardInterrupt:
        logger.info("⏹️ Тестирование прервано пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    # Запускаем финальный тест
    results = asyncio.run(main())
