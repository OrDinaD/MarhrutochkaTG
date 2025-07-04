#!/usr/bin/env python3
"""
Улучшенный скрипт для исследования функционала сайта маршруточки через Playwright
с более точной обработкой форм авторизации
"""

import asyncio
import time
from playwright.async_api import async_playwright

class MarshaExplorerV2:
    def __init__(self):
        self.login = "+375299605390"
        self.password = "Zxcvbnm,1"
        self.base_url = "https://билет.маршруточка.бел"
        self.profile_url = "https://билет.маршруточка.бел/profile"
        
    async def run(self):
        """Основной метод для запуска исследования"""
        async with async_playwright() as p:
            # Запускаем браузер с головой для лучшего отображения
            browser = await p.chromium.launch(
                headless=False, 
                slow_mo=500,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                print("🚀 Начинаем улучшенное исследование сайта маршруточки...")
                
                # 1. Переходим на главную страницу
                await self.visit_main_page(page)
                
                # 2. Авторизуемся с улучшенной логикой
                await self.advanced_login(page)
                
                # 3. Исследуем профиль после авторизации
                await self.explore_authenticated_profile(page)
                
                # 4. Исследуем функционал поиска билетов
                await self.explore_ticket_booking(page)
                
                # 5. Создаем подробный отчет
                await self.generate_detailed_report(page)
                
                print("✅ Улучшенное исследование завершено успешно!")
                
            except Exception as e:
                print(f"❌ Ошибка во время исследования: {e}")
                await page.screenshot(path="error_screenshot_v2.png", full_page=True)
                
            finally:
                # Держим браузер открытым для просмотра результатов
                print("🔍 Браузер остается открытым для просмотра результатов...")
                input("📋 Нажмите Enter для закрытия браузера...")
                await browser.close()
    
    async def visit_main_page(self, page):
        """Посещение главной страницы с детальным анализом"""
        print(f"📱 Переходим на главную страницу: {self.base_url}")
        await page.goto(self.base_url, wait_until='networkidle', timeout=30000)
        await page.wait_for_load_state('domcontentloaded')
        
        # Анализируем структуру страницы
        print("🔍 Анализируем структуру главной страницы...")
        
        # Получаем все элементы формы
        forms = await page.query_selector_all('form')
        print(f"📋 Найдено форм: {len(forms)}")
        
        # Получаем все кнопки
        buttons = await page.query_selector_all('button')
        print(f"🔘 Найдено кнопок: {len(buttons)}")
        
        # Ищем элементы авторизации
        login_elements = await page.query_selector_all('*[class*="login"], *[id*="login"], *[class*="auth"], *[id*="auth"]')
        print(f"🔐 Найдено элементов авторизации: {len(login_elements)}")
        
        # Делаем скриншот главной страницы
        await page.screenshot(path="main_page_v2.png", full_page=True)
        print("📸 Скриншот главной страницы сохранен как main_page_v2.png")
        
        # Ждем немного для полной загрузки
        await page.wait_for_timeout(2000)
    
    async def advanced_login(self, page):
        """Улучшенная логика авторизации"""
        print("🔐 Начинаем улучшенную авторизацию...")
        
        try:
            # Сначала ищем кнопку "Войти" и кликаем по ней
            login_button_clicked = False
            
            # Различные способы найти кнопку входа
            login_button_selectors = [
                'text="Войти"',
                '[class*="login"]',
                'a:has-text("Войти")',
                'button:has-text("Войти")',
                '*[onclick*="login"]'
            ]
            
            for selector in login_button_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        print(f"🎯 Найдена кнопка входа: {selector}")
                        await element.click()
                        await page.wait_for_timeout(1000)
                        login_button_clicked = True
                        break
                except:
                    continue
            
            if login_button_clicked:
                print("✅ Кнопка входа нажата, ищем форму авторизации...")
                await page.wait_for_timeout(2000)
            
            # Теперь ищем поля для ввода данных
            await self.fill_advanced_login_form(page)
            
        except Exception as e:
            print(f"⚠️ Ошибка при улучшенной авторизации: {e}")
            await page.screenshot(path="advanced_login_error.png", full_page=True)
    
    async def fill_advanced_login_form(self, page):
        """Улучшенное заполнение формы авторизации"""
        print("📝 Заполняем форму авторизации (улучшенный метод)...")
        
        # Ждем появления формы
        await page.wait_for_timeout(2000)
        
        # Различные селекторы для поля телефона
        phone_selectors = [
            'input[name="phone"]',
            'input[type="tel"]',
            'input[placeholder*="телефон"]',
            'input[placeholder*="Телефон"]',
            'input[id*="phone"]',
            'input[class*="phone"]'
        ]
        
        # Заполняем телефон
        phone_filled = False
        for selector in phone_selectors:
            try:
                phone_field = await page.wait_for_selector(selector, timeout=3000)
                if phone_field:
                    # Очищаем поле и вводим номер
                    await phone_field.click()
                    await phone_field.clear()
                    await phone_field.type(self.login, delay=100)
                    print(f"✅ Телефон введен через селектор: {selector}")
                    phone_filled = True
                    break
            except:
                continue
        
        if not phone_filled:
            print("❌ Не удалось найти поле для телефона")
            # Пробуем универсальный подход
            try:
                await page.fill('input[type="text"]', self.login)
                print("✅ Телефон введен через универсальный селектор")
                phone_filled = True
            except:
                pass
        
        # Различные селекторы для поля пароля
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="пароль"]',
            'input[placeholder*="Пароль"]',
            'input[id*="password"]',
            'input[class*="password"]'
        ]
        
        # Заполняем пароль
        password_filled = False
        for selector in password_selectors:
            try:
                password_field = await page.wait_for_selector(selector, timeout=3000)
                if password_field:
                    await password_field.click()
                    await password_field.clear()
                    await password_field.type(self.password, delay=100)
                    print(f"✅ Пароль введен через селектор: {selector}")
                    password_filled = True
                    break
            except:
                continue
        
        if not password_filled:
            print("❌ Не удалось найти поле для пароля")
        
        # Делаем скриншот перед отправкой формы
        await page.screenshot(path="before_login_submit.png", full_page=True)
        print("📸 Скриншот перед отправкой формы сохранен")
        
        if phone_filled and password_filled:
            # Ищем кнопку отправки формы
            await self.submit_login_form(page)
        else:
            print("❌ Не удалось заполнить все поля формы")
    
    async def submit_login_form(self, page):
        """Отправка формы авторизации"""
        print("🚀 Отправляем форму авторизации...")
        
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Войти")',
            'button:has-text("Вход")',
            '*[onclick*="submit"]',
            'form button'
        ]
        
        form_submitted = False
        for selector in submit_selectors:
            try:
                submit_button = await page.wait_for_selector(selector, timeout=3000)
                if submit_button:
                    await submit_button.click()
                    print(f"✅ Форма отправлена через: {selector}")
                    form_submitted = True
                    break
            except:
                continue
        
        if not form_submitted:
            # Пробуем нажать Enter в поле пароля
            try:
                await page.keyboard.press('Enter')
                print("✅ Форма отправлена через Enter")
                form_submitted = True
            except:
                print("❌ Не удалось отправить форму")
        
        if form_submitted:
            # Ждем загрузки после авторизации
            await page.wait_for_load_state('networkidle', timeout=10000)
            await page.wait_for_timeout(3000)
            
            # Проверяем результат авторизации
            current_url = page.url
            page_title = await page.title()
            
            print(f"🌐 URL после авторизации: {current_url}")
            print(f"📄 Заголовок после авторизации: {page_title}")
            
            # Делаем скриншот после авторизации
            await page.screenshot(path="after_advanced_login.png", full_page=True)
            print("📸 Скриншот после авторизации сохранен")
            
            # Проверяем, успешна ли авторизация
            if "404" not in page_title and "error" not in page_title.lower():
                print("✅ Авторизация, вероятно, прошла успешно!")
                return True
            else:
                print("⚠️ Возможны проблемы с авторизацией")
                return False
        
        return False
    
    async def explore_authenticated_profile(self, page):
        """Исследование профиля после авторизации"""
        print("👤 Исследуем профиль пользователя после авторизации...")
        
        try:
            # Пробуем перейти на страницу профиля
            try:
                await page.goto(self.profile_url, wait_until='networkidle', timeout=15000)
                print(f"📍 Переход на профиль: {self.profile_url}")
            except:
                print("⚠️ Не удалось перейти на страницу профиля, остаемся на текущей")
            
            # Анализируем содержимое страницы
            page_content = await page.content()
            page_title = await page.title()
            current_url = page.url
            
            print(f"📄 Текущий заголовок: {page_title}")
            print(f"🌐 Текущий URL: {current_url}")
            
            # Ищем элементы профиля
            profile_elements = await self.find_profile_elements(page)
            
            # Ищем информацию о пользователе
            user_info = await self.extract_user_info(page)
            
            print("📋 Информация о пользователе:")
            for key, value in user_info.items():
                print(f"   {key}: {value}")
            
            # Делаем скриншот профиля
            await page.screenshot(path="authenticated_profile.png", full_page=True)
            print("📸 Скриншот аутентифицированного профиля сохранен")
            
        except Exception as e:
            print(f"⚠️ Ошибка при исследовании профиля: {e}")
            await page.screenshot(path="profile_exploration_error.png", full_page=True)
    
    async def find_profile_elements(self, page):
        """Поиск элементов профиля"""
        profile_elements = {}
        
        # Элементы, которые могут содержать информацию профиля
        profile_selectors = {
            'Меню профиля': ['nav', '.profile-menu', '.user-menu'],
            'Имя пользователя': ['.username', '.user-name', '.profile-name'],
            'Контактная информация': ['.contact', '.phone', '.email'],
            'Баланс': ['.balance', '.money', '.account-balance'],
            'История поездок': ['.trips', '.history', '.bookings']
        }
        
        for element_type, selectors in profile_selectors.items():
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        profile_elements[element_type] = len(elements)
                        break
                except:
                    continue
        
        return profile_elements
    
    async def extract_user_info(self, page):
        """Извлечение информации о пользователе"""
        user_info = {}
        
        try:
            # Получаем весь текст страницы для анализа
            page_text = await page.text_content('body')
            
            # Ищем упоминания номера телефона
            if self.login.replace('+', '') in page_text:
                user_info['Телефон найден'] = 'Да'
            
            # Ищем элементы с информацией о пользователе
            info_selectors = {
                'Заголовок страницы': 'title',
                'Основное содержимое': 'main, .main, .content, .container'
            }
            
            for info_type, selector in info_selectors.items():
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and len(text.strip()) > 0:
                            user_info[info_type] = text.strip()[:200] + '...' if len(text.strip()) > 200 else text.strip()
                except:
                    continue
            
            # Проверяем наличие форм и кнопок
            forms_count = len(await page.query_selector_all('form'))
            buttons_count = len(await page.query_selector_all('button'))
            links_count = len(await page.query_selector_all('a'))
            
            user_info['Количество форм'] = forms_count
            user_info['Количество кнопок'] = buttons_count
            user_info['Количество ссылок'] = links_count
            
        except Exception as e:
            user_info['Ошибка извлечения'] = str(e)
        
        return user_info
    
    async def explore_ticket_booking(self, page):
        """Исследование функционала бронирования билетов"""
        print("🎫 Исследуем функционал бронирования билетов...")
        
        try:
            # Возвращаемся на главную страницу для тестирования поиска
            await page.goto(self.base_url, wait_until='networkidle')
            
            # Ищем форму поиска маршрутов
            search_form = await self.find_search_form(page)
            
            if search_form:
                print("🔍 Форма поиска найдена, тестируем функционал...")
                await self.test_search_functionality(page)
            else:
                print("❌ Форма поиска не найдена")
            
            # Делаем скриншот страницы поиска
            await page.screenshot(path="ticket_booking_exploration.png", full_page=True)
            print("📸 Скриншот исследования бронирования сохранен")
            
        except Exception as e:
            print(f"⚠️ Ошибка при исследовании бронирования: {e}")
    
    async def find_search_form(self, page):
        """Поиск формы поиска маршрутов"""
        search_elements = {}
        
        # Селекторы для элементов поиска
        search_selectors = {
            'Откуда': ['input[placeholder*="Откуда"]', 'input[name*="from"]'],
            'Куда': ['input[placeholder*="Куда"]', 'input[name*="to"]'],
            'Дата': ['input[type="date"]', 'input[placeholder*="дата"]'],
            'Кнопка поиска': ['button:has-text("Найти")', 'input[type="submit"]']
        }
        
        for element_type, selectors in search_selectors.items():
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        search_elements[element_type] = selector
                        print(f"✅ Найден элемент '{element_type}': {selector}")
                        break
                except:
                    continue
        
        return search_elements
    
    async def test_search_functionality(self, page):
        """Тестирование функционала поиска"""
        print("🧪 Тестируем функционал поиска маршрутов...")
        
        try:
            # Пробуем заполнить поля поиска тестовыми данными
            test_data = {
                'from': 'Минск',
                'to': 'Гродно'
            }
            
            # Заполняем поле "Откуда"
            from_selectors = ['input[placeholder*="Откуда"]', 'input[name*="from"]']
            for selector in from_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        await field.fill(test_data['from'])
                        print(f"✅ Поле 'Откуда' заполнено: {test_data['from']}")
                        break
                except:
                    continue
            
            # Заполняем поле "Куда"
            to_selectors = ['input[placeholder*="Куда"]', 'input[name*="to"]']
            for selector in to_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        await field.fill(test_data['to'])
                        print(f"✅ Поле 'Куда' заполнено: {test_data['to']}")
                        break
                except:
                    continue
            
            # Делаем скриншот заполненной формы
            await page.screenshot(path="filled_search_form.png", full_page=True)
            print("📸 Скриншот заполненной формы поиска сохранен")
            
        except Exception as e:
            print(f"⚠️ Ошибка при тестировании поиска: {e}")
    
    async def generate_detailed_report(self, page):
        """Генерация подробного отчета"""
        print("📊 Генерируем подробный отчет...")
        
        try:
            # Собираем статистику
            report = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'final_url': page.url,
                'page_title': await page.title(),
                'total_links': len(await page.query_selector_all('a')),
                'total_forms': len(await page.query_selector_all('form')),
                'total_buttons': len(await page.query_selector_all('button')),
                'total_inputs': len(await page.query_selector_all('input')),
                'has_search_form': bool(await page.query_selector('input[placeholder*="Откуда"]')),
                'has_login_form': bool(await page.query_selector('input[type="password"]'))
            }
            
            print("📋 Финальный отчет:")
            print("=" * 50)
            for key, value in report.items():
                print(f"{key}: {value}")
            print("=" * 50)
            
            # Финальный скриншот
            await page.screenshot(path="final_report_screenshot.png", full_page=True)
            print("📸 Финальный скриншот отчета сохранен")
            
        except Exception as e:
            print(f"⚠️ Ошибка при генерации отчета: {e}")

async def main():
    """Главная функция"""
    explorer = MarshaExplorerV2()
    await explorer.run()

if __name__ == "__main__":
    print("🎭 Запуск улучшенного исследователя сайта маршруточки...")
    print("=" * 60)
    asyncio.run(main())
