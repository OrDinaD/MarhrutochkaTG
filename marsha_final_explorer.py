#!/usr/bin/env python3
"""
Финальный скрипт для авторизации и исследования функционала маршруточки
на основе детального анализа сайта
"""

import asyncio
import json
from playwright.async_api import async_playwright

class MarshaFinalExplorer:
    def __init__(self):
        self.base_url = "https://билет.маршруточка.бел"
        self.login = "+375299605390"
        self.password = "Zxcvbnm,1"
        self.results = {}
        
    async def run(self):
        """Основной метод"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=500)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                print("🎯 ФИНАЛЬНОЕ ИССЛЕДОВАНИЕ САЙТА МАРШРУТОЧКИ")
                print("=" * 60)
                
                # 1. Основная авторизация
                success = await self.perform_login(page)
                
                if success:
                    print("✅ Авторизация успешна! Исследуем функционал...")
                    
                    # 2. Исследование авторизованного функционала
                    await self.explore_authenticated_features(page)
                    
                    # 3. Поиск информации о бронях
                    await self.find_booking_information(page)
                    
                else:
                    print("❌ Авторизация не удалась, исследуем гостевой функционал...")
                    await self.explore_guest_features(page)
                
                # 4. Тестирование поиска маршрутов
                await self.test_route_search(page)
                
                # 5. Генерация финального отчета
                await self.generate_final_report(page)
                
                print("✅ Исследование завершено!")
                
            except Exception as e:
                print(f"❌ Критическая ошибка: {e}")
                await page.screenshot(path="critical_error.png", full_page=True)
                
            finally:
                print("🔍 Браузер остается открытым для просмотра...")
                input("Нажмите Enter для закрытия...")
                await browser.close()
    
    async def perform_login(self, page):
        """Выполнение авторизации на основе анализа"""
        print("\n🔐 ВЫПОЛНЕНИЕ АВТОРИЗАЦИИ")
        print("-" * 40)
        
        try:
            # Переходим на главную
            await page.goto(self.base_url, wait_until='networkidle')
            
            # Кликаем на кнопку Войти
            print("🖱️ Кликаем на кнопку 'Войти'...")
            await page.click('text="Войти"')
            await page.wait_for_timeout(1000)
            
            # Заполняем форму (знаем точные селекторы из анализа)
            print("📝 Заполняем форму авторизации...")
            
            # Поле телефона (form.enterForm input[name="phone"])
            phone_selector = 'form.enterForm input[name="phone"]'
            await page.fill(phone_selector, self.login)
            print(f"✅ Телефон заполнен: {self.login}")
            
            # Поле пароля (form.enterForm input[name="password"])
            password_selector = 'form.enterForm input[name="password"]'
            await page.fill(password_selector, self.password)
            print("✅ Пароль заполнен")
            
            # Делаем скриншот перед отправкой
            await page.screenshot(path="final_before_submit.png", full_page=True)
            print("📸 Скриншот перед отправкой сохранен")
            
            # Отправляем форму (используем submit кнопку или Enter)
            print("🚀 Отправляем форму...")
            
            # Пробуем разные способы отправки
            submit_methods = [
                ('click', 'form.enterForm input[type="submit"]'),
                ('click', 'form.enterForm .enterButton'),
                ('press', 'Enter')
            ]
            
            form_submitted = False
            for method, selector in submit_methods:
                try:
                    if method == 'click':
                        await page.click(selector)
                    elif method == 'press':
                        await page.keyboard.press(selector)
                    
                    print(f"✅ Форма отправлена методом: {method} {selector}")
                    form_submitted = True
                    break
                    
                except Exception as e:
                    print(f"⚠️ Метод {method} {selector} не сработал: {str(e)[:50]}...")
                    continue
            
            if not form_submitted:
                print("❌ Не удалось отправить форму")
                return False
            
            # Ждем ответа
            print("⏳ Ждем ответа сервера...")
            await page.wait_for_load_state('networkidle', timeout=10000)
            await page.wait_for_timeout(2000)
            
            # Проверяем результат
            return await self.check_login_result(page)
            
        except Exception as e:
            print(f"❌ Ошибка при авторизации: {e}")
            await page.screenshot(path="login_error_final.png", full_page=True)
            return False
    
    async def check_login_result(self, page):
        """Проверка результата авторизации"""
        print("\n📊 ПРОВЕРКА РЕЗУЛЬТАТА АВТОРИЗАЦИИ")
        print("-" * 40)
        
        current_url = page.url
        title = await page.title()
        
        print(f"🌐 Текущий URL: {current_url}")
        print(f"📄 Заголовок: {title}")
        
        # Скриншот после авторизации
        await page.screenshot(path="final_after_login.png", full_page=True)
        print("📸 Скриншот после авторизации сохранен")
        
        # Ищем признаки успешной авторизации
        success_indicators = [
            'text="Выйти"',
            'text="Профиль"',
            'text="Мой профиль"',
            '.user-info',
            '.profile-info'
        ]
        
        for indicator in success_indicators:
            try:
                element = await page.query_selector(indicator)
                if element:
                    print(f"✅ Найден индикатор успешной авторизации: {indicator}")
                    self.results['login_success'] = True
                    self.results['login_indicator'] = indicator
                    return True
            except:
                continue
        
        # Проверяем, не появилось ли сообщение об ошибке
        error_patterns = ['error', 'ошибка', 'неверный', 'неправильн']
        page_content = await page.content()
        
        for pattern in error_patterns:
            if pattern.lower() in page_content.lower():
                print(f"❌ Возможна ошибка авторизации (найден паттерн: {pattern})")
                self.results['login_success'] = False
                self.results['login_error'] = pattern
                return False
        
        # Если изменился URL или заголовок, возможно авторизация прошла
        if current_url != self.base_url or '404' not in title:
            print("🤔 Возможно, авторизация прошла (изменился URL или заголовок)")
            self.results['login_success'] = 'maybe'
            return True
        
        print("❌ Признаки успешной авторизации не найдены")
        self.results['login_success'] = False
        return False
    
    async def explore_authenticated_features(self, page):
        """Исследование функций для авторизованных пользователей"""
        print("\n👤 ИССЛЕДОВАНИЕ АВТОРИЗОВАННОГО ФУНКЦИОНАЛА")
        print("-" * 50)
        
        # Пробуем перейти на страницы профиля
        profile_urls = [
            f"{self.base_url}/profile",
            f"{self.base_url}/user",
            f"{self.base_url}/account",
            f"{self.base_url}/dashboard"
        ]
        
        for url in profile_urls:
            try:
                print(f"🔍 Проверяем URL: {url}")
                await page.goto(url, wait_until='networkidle', timeout=5000)
                
                title = await page.title()
                current_url = page.url
                
                if '404' not in title and 'error' not in title.lower():
                    print(f"✅ Доступная страница: {url}")
                    print(f"   Заголовок: {title}")
                    
                    # Скриншот страницы
                    filename = f"auth_page_{url.split('/')[-1]}.png"
                    await page.screenshot(path=filename, full_page=True)
                    print(f"📸 Скриншот сохранен: {filename}")
                    
                    # Анализируем содержимое
                    await self.analyze_page_content(page, url)
                    
                    self.results[f'accessible_page_{url.split("/")[-1]}'] = {
                        'url': current_url,
                        'title': title,
                        'accessible': True
                    }
                else:
                    print(f"❌ Недоступная страница: {url} (заголовок: {title})")
                    self.results[f'accessible_page_{url.split("/")[-1]}'] = {
                        'url': url,
                        'title': title,
                        'accessible': False
                    }
                    
            except Exception as e:
                print(f"❌ Ошибка при проверке {url}: {str(e)[:50]}...")
                continue
            
            await page.wait_for_timeout(1000)
    
    async def analyze_page_content(self, page, url):
        """Анализ содержимого страницы"""
        print(f"   🔍 Анализируем содержимое {url}...")
        
        try:
            # Ищем элементы, связанные с пользователем
            user_elements = await page.query_selector_all(
                '*[class*="user"], *[class*="profile"], *[id*="user"], *[id*="profile"]'
            )
            print(f"   📋 Найдено пользовательских элементов: {len(user_elements)}")
            
            # Ищем информацию о бронях/билетах
            booking_elements = await page.query_selector_all(
                '*[class*="booking"], *[class*="ticket"], *[class*="order"], *[class*="trip"]'
            )
            print(f"   🎫 Найдено элементов с бронями: {len(booking_elements)}")
            
            # Получаем основной текст страницы
            main_text = await page.text_content('body')
            
            # Ищем упоминания номера телефона
            if self.login.replace('+', '') in main_text:
                print(f"   ✅ Найдено упоминание номера телефона: {self.login}")
                
            # Ищем ключевые слова
            keywords = ['бронь', 'билет', 'поездка', 'маршрут', 'баланс', 'история']
            found_keywords = []
            for keyword in keywords:
                if keyword in main_text.lower():
                    found_keywords.append(keyword)
            
            if found_keywords:
                print(f"   🔍 Найдены ключевые слова: {', '.join(found_keywords)}")
                
        except Exception as e:
            print(f"   ⚠️ Ошибка анализа содержимого: {e}")
    
    async def find_booking_information(self, page):
        """Поиск информации о бронях"""
        print("\n🎫 ПОИСК ИНФОРМАЦИИ О БРОНЯХ")
        print("-" * 40)
        
        # Возвращаемся на главную для поиска броней
        await page.goto(self.base_url, wait_until='networkidle')
        
        # Ищем элементы, связанные с бронями
        booking_selectors = [
            'text="Мои поездки"',
            'text="Мои билеты"',
            'text="История"',
            'text="Брони"',
            '*[href*="booking"]',
            '*[href*="ticket"]',
            '*[href*="history"]'
        ]
        
        for selector in booking_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    print(f"✅ Найден элемент броней: {selector}")
                    
                    # Кликаем по элементу
                    await element.click()
                    await page.wait_for_load_state('networkidle')
                    
                    # Анализируем страницу броней
                    await self.analyze_bookings_page(page)
                    break
                    
            except Exception as e:
                print(f"⚠️ Ошибка с селектором {selector}: {str(e)[:30]}...")
                continue
        
        # Если не нашли специальных элементов, ищем общую информацию
        await self.search_booking_info_general(page)
    
    async def analyze_bookings_page(self, page):
        """Анализ страницы с бронями"""
        print("   📋 Анализируем страницу с бронями...")
        
        title = await page.title()
        url = page.url
        
        print(f"   📄 Заголовок: {title}")
        print(f"   🌐 URL: {url}")
        
        # Скриншот страницы броней
        await page.screenshot(path="bookings_analysis.png", full_page=True)
        print("   📸 Скриншот страницы броней сохранен")
        
        # Ищем конкретные брони
        booking_containers = [
            '.booking-item',
            '.ticket-item',
            '.order-item',
            '.trip-item',
            '*[class*="booking"]',
            '*[class*="ticket"]'
        ]
        
        total_bookings = 0
        for container in booking_containers:
            try:
                elements = await page.query_selector_all(container)
                if elements:
                    total_bookings += len(elements)
                    print(f"   🎫 Найдено броней в {container}: {len(elements)}")
                    
                    # Анализируем первые несколько броней
                    for i, booking in enumerate(elements[:3]):
                        try:
                            text = await booking.text_content()
                            if text and text.strip():
                                print(f"      Бронь {i+1}: {text.strip()[:100]}...")
                        except:
                            continue
            except:
                continue
        
        self.results['bookings'] = {
            'total_found': total_bookings,
            'page_title': title,
            'page_url': url
        }
        
        if total_bookings == 0:
            print("   ❌ Конкретные брони не найдены")
        else:
            print(f"   ✅ Всего найдено броней: {total_bookings}")
    
    async def search_booking_info_general(self, page):
        """Общий поиск информации о бронях"""
        print("   🔍 Общий поиск информации о бронях...")
        
        # Получаем весь текст страницы
        page_text = await page.text_content('body')
        
        # Ищем ключевые слова, связанные с бронями
        booking_keywords = [
            'бронирование', 'бронь', 'билет', 'поездка', 'маршрут',
            'заказ', 'резерв', 'место', 'рейс', 'автобус'
        ]
        
        found_info = []
        for keyword in booking_keywords:
            if keyword in page_text.lower():
                # Ищем контекст вокруг найденного слова
                import re
                pattern = rf'.{0,50}{re.escape(keyword)}.{0,50}'
                matches = re.findall(pattern, page_text.lower(), re.IGNORECASE)
                
                if matches:
                    found_info.extend(matches[:2])  # Берем первые 2 совпадения
        
        if found_info:
            print("   ✅ Найдена информация о бронях:")
            for info in found_info[:3]:  # Показываем первые 3
                print(f"      {info.strip()}")
        else:
            print("   ❌ Общая информация о бронях не найдена")
    
    async def explore_guest_features(self, page):
        """Исследование гостевого функционала"""
        print("\n👥 ИССЛЕДОВАНИЕ ГОСТЕВОГО ФУНКЦИОНАЛА")
        print("-" * 40)
        
        await page.goto(self.base_url, wait_until='networkidle')
        
        # Анализируем функцию проверки статуса бронирования
        print("🔍 Ищем функцию проверки статуса бронирования...")
        
        try:
            # Ищем форму проверки статуса (из анализа знаем, что есть форма #6)
            status_form = await page.query_selector('input[name="order-slug"]')
            if status_form:
                print("✅ Найдена форма проверки статуса бронирования")
                
                # Заполняем тестовыми данными
                await status_form.fill('TEST12345')
                print("   📝 Заполнено поле номера бронирования")
                
                # Ищем поле для телефона
                phone_digits_field = await page.query_selector('input[placeholder*="цифры телефона"]')
                if phone_digits_field:
                    await phone_digits_field.fill('5390')  # Последние 4 цифры
                    print("   📝 Заполнено поле последних цифр телефона")
                
                # Скриншот формы статуса
                await page.screenshot(path="status_check_form.png", full_page=True)
                print("   📸 Скриншот формы проверки статуса сохранен")
                
            else:
                print("❌ Форма проверки статуса не найдена")
                
        except Exception as e:
            print(f"⚠️ Ошибка при исследовании проверки статуса: {e}")
    
    async def test_route_search(self, page):
        """Тестирование поиска маршрутов"""
        print("\n🚌 ТЕСТИРОВАНИЕ ПОИСКА МАРШРУТОВ")
        print("-" * 40)
        
        await page.goto(self.base_url, wait_until='networkidle')
        
        try:
            # Ищем форму поиска (из анализа знаем структуру)
            search_form = await page.query_selector('#reservations')
            if search_form:
                print("✅ Найдена форма поиска маршрутов")
                
                # Заполняем поля (знаем селекторы из анализа)
                places_field = await page.query_selector('input[name="places"]')
                date_field = await page.query_selector('input[name="date"]')
                
                if places_field:
                    await places_field.fill('Минск - Гродно')
                    print("   📝 Заполнено поле маршрута: Минск - Гродно")
                
                if date_field:
                    # Заполняем завтрашней датой
                    from datetime import datetime, timedelta
                    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                    await date_field.fill(tomorrow)
                    print(f"   📝 Заполнено поле даты: {tomorrow}")
                
                # Скриншот формы поиска
                await page.screenshot(path="search_form_filled.png", full_page=True)
                print("   📸 Скриншот заполненной формы поиска сохранен")
                
                # Не отправляем форму, чтобы не переходить на другую страницу
                print("   🔍 Форма поиска готова к использованию")
                
            else:
                print("❌ Форма поиска маршрутов не найдена")
                
        except Exception as e:
            print(f"⚠️ Ошибка при тестировании поиска: {e}")
    
    async def generate_final_report(self, page):
        """Генерация финального отчета"""
        print("\n📊 ГЕНЕРАЦИЯ ФИНАЛЬНОГО ОТЧЕТА")
        print("=" * 50)
        
        # Собираем итоговую статистику
        current_url = page.url
        title = await page.title()
        
        report = {
            'timestamp': '2025-07-02',
            'final_url': current_url,
            'final_title': title,
            'login_attempted': True,
            'login_success': self.results.get('login_success', False),
            'accessible_pages': [k for k, v in self.results.items() if k.startswith('accessible_page') and v.get('accessible')],
            'bookings_found': self.results.get('bookings', {}).get('total_found', 0),
            'features_analyzed': [
                'Авторизация',
                'Поиск маршрутов', 
                'Проверка статуса бронирования',
                'Профиль пользователя',
                'Информация о бронях'
            ]
        }
        
        print("📋 ИТОГОВЫЙ ОТЧЕТ:")
        print("-" * 30)
        for key, value in report.items():
            if isinstance(value, list):
                print(f"{key}: {len(value)} элементов")
                for item in value:
                    print(f"   - {item}")
            else:
                print(f"{key}: {value}")
        
        # Сохраняем отчет в JSON
        with open('marsha_exploration_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("\n💾 Отчет сохранен в marsha_exploration_report.json")
        
        # Финальный скриншот
        await page.screenshot(path="final_exploration_result.png", full_page=True)
        print("📸 Финальный скриншот сохранен")

async def main():
    explorer = MarshaFinalExplorer()
    await explorer.run()

if __name__ == "__main__":
    asyncio.run(main())
