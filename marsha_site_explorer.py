#!/usr/bin/env python3
"""
Скрипт для исследования функционала сайта маршруточки через Playwright
"""

import asyncio
import time
from playwright.async_api import async_playwright

class MarshaExplorer:
    def __init__(self):
        self.login = "+375299605390"
        self.password = "Zxcvbnm,1"
        self.base_url = "https://билет.маршруточка.бел"
        self.profile_url = "https://билет.маршруточка.бел/profile"
        
    async def run(self):
        """Основной метод для запуска исследования"""
        async with async_playwright() as p:
            # Запускаем браузер с головой для лучшего отображения
            browser = await p.chromium.launch(headless=False, slow_mo=1000)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                print("🚀 Начинаем исследование сайта маршруточки...")
                
                # 1. Переходим на главную страницу
                await self.visit_main_page(page)
                
                # 2. Авторизуемся
                await self.login_to_account(page)
                
                # 3. Исследуем профиль пользователя
                await self.explore_profile(page)
                
                # 4. Исследуем информацию о бронях
                await self.explore_bookings(page)
                
                # 5. Исследуем общий функционал сайта
                await self.explore_site_functionality(page)
                
                print("✅ Исследование завершено успешно!")
                
            except Exception as e:
                print(f"❌ Ошибка во время исследования: {e}")
                await page.screenshot(path="error_screenshot.png")
                
            finally:
                # Держим браузер открытым для просмотра результатов
                input("📋 Нажмите Enter для закрытия браузера...")
                await browser.close()
    
    async def visit_main_page(self, page):
        """Посещение главной страницы"""
        print(f"📱 Переходим на главную страницу: {self.base_url}")
        await page.goto(self.base_url, wait_until='networkidle')
        await page.wait_for_load_state('domcontentloaded')
        
        # Делаем скриншот главной страницы
        await page.screenshot(path="main_page.png", full_page=True)
        print("📸 Скриншот главной страницы сохранен как main_page.png")
        
        # Изучаем структуру главной страницы
        title = await page.title()
        print(f"📄 Заголовок страницы: {title}")
        
        # Ждем немного для полной загрузки
        await page.wait_for_timeout(2000)
    
    async def login_to_account(self, page):
        """Авторизация в аккаунте"""
        print("🔐 Начинаем процесс авторизации...")
        
        try:
            # Ищем кнопку входа или ссылку на авторизацию
            login_selectors = [
                'a[href*="login"]',
                'button:has-text("Войти")',
                'a:has-text("Войти")',
                '.login',
                '#login',
                'a:has-text("Вход")',
                'button:has-text("Вход")',
                '[data-testid="login"]'
            ]
            
            login_element = None
            for selector in login_selectors:
                try:
                    login_element = await page.wait_for_selector(selector, timeout=3000)
                    if login_element:
                        print(f"🎯 Найдена кнопка входа: {selector}")
                        break
                except:
                    continue
            
            if login_element:
                await login_element.click()
                await page.wait_for_load_state('networkidle')
            else:
                print("🔍 Кнопка входа не найдена, пробуем перейти напрямую на страницу авторизации")
                # Пробуем различные варианты URL для входа
                login_urls = [
                    f"{self.base_url}/login",
                    f"{self.base_url}/auth",
                    f"{self.base_url}/signin"
                ]
                
                for url in login_urls:
                    try:
                        await page.goto(url)
                        await page.wait_for_load_state('networkidle')
                        if "login" in page.url.lower() or "auth" in page.url.lower():
                            break
                    except:
                        continue
            
            # Ищем поля для ввода логина и пароля
            await self.fill_login_form(page)
            
        except Exception as e:
            print(f"⚠️ Ошибка при авторизации: {e}")
            await page.screenshot(path="login_error.png")
    
    async def fill_login_form(self, page):
        """Заполнение формы авторизации"""
        print("📝 Заполняем форму авторизации...")
        
        # Возможные селекторы для поля логина/телефона
        login_selectors = [
            'input[type="tel"]',
            'input[name*="phone"]',
            'input[name*="login"]',
            'input[name*="username"]',
            'input[placeholder*="телефон"]',
            'input[placeholder*="номер"]',
            'input[id*="phone"]',
            'input[id*="login"]'
        ]
        
        # Возможные селекторы для поля пароля
        password_selectors = [
            'input[type="password"]',
            'input[name*="password"]',
            'input[name*="pass"]',
            'input[id*="password"]',
            'input[placeholder*="пароль"]'
        ]
        
        # Заполняем логин
        login_field = None
        for selector in login_selectors:
            try:
                login_field = await page.wait_for_selector(selector, timeout=3000)
                if login_field:
                    await login_field.fill(self.login)
                    print(f"✅ Логин введен в поле: {selector}")
                    break
            except:
                continue
        
        if not login_field:
            print("❌ Поле для логина не найдено")
            return
        
        # Заполняем пароль
        password_field = None
        for selector in password_selectors:
            try:
                password_field = await page.wait_for_selector(selector, timeout=3000)
                if password_field:
                    await password_field.fill(self.password)
                    print(f"✅ Пароль введен в поле: {selector}")
                    break
            except:
                continue
        
        if not password_field:
            print("❌ Поле для пароля не найдено")
            return
        
        # Ищем кнопку отправки формы
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Войти")',
            'button:has-text("Вход")',
            'button:has-text("Отправить")',
            '.submit-btn',
            '#submit'
        ]
        
        for selector in submit_selectors:
            try:
                submit_button = await page.wait_for_selector(selector, timeout=3000)
                if submit_button:
                    await submit_button.click()
                    print(f"🚀 Форма отправлена через: {selector}")
                    break
            except:
                continue
        
        # Ждем загрузки после авторизации
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)
        
        # Проверяем, успешна ли авторизация
        current_url = page.url
        print(f"🌐 Текущий URL после авторизации: {current_url}")
        
        # Делаем скриншот после авторизации
        await page.screenshot(path="after_login.png", full_page=True)
        print("📸 Скриншот после авторизации сохранен как after_login.png")
    
    async def explore_profile(self, page):
        """Исследование профиля пользователя"""
        print("👤 Исследуем профиль пользователя...")
        
        try:
            # Переходим на страницу профиля
            await page.goto(self.profile_url, wait_until='networkidle')
            await page.wait_for_load_state('domcontentloaded')
            
            # Делаем скриншот профиля
            await page.screenshot(path="profile_page.png", full_page=True)
            print("📸 Скриншот профиля сохранен как profile_page.png")
            
            # Извлекаем информацию о профиле
            profile_info = await self.extract_profile_info(page)
            print("📋 Информация профиля:")
            for key, value in profile_info.items():
                print(f"   {key}: {value}")
            
        except Exception as e:
            print(f"⚠️ Ошибка при исследовании профиля: {e}")
            await page.screenshot(path="profile_error.png")
    
    async def extract_profile_info(self, page):
        """Извлечение информации из профиля"""
        profile_data = {}
        
        try:
            # Ищем различные элементы профиля
            selectors_to_check = {
                'Имя': ['[data-testid="name"]', '.name', '#name', '.user-name'],
                'Телефон': ['[data-testid="phone"]', '.phone', '#phone', '.user-phone'],
                'Email': ['[data-testid="email"]', '.email', '#email', '.user-email'],
                'Баланс': ['[data-testid="balance"]', '.balance', '#balance', '.user-balance']
            }
            
            for field_name, selectors in selectors_to_check.items():
                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            text = await element.text_content()
                            if text and text.strip():
                                profile_data[field_name] = text.strip()
                                break
                    except:
                        continue
            
            # Получаем заголовок страницы
            title = await page.title()
            profile_data['Заголовок страницы'] = title
            
        except Exception as e:
            print(f"⚠️ Ошибка при извлечении данных профиля: {e}")
        
        return profile_data
    
    async def explore_bookings(self, page):
        """Исследование информации о бронях"""
        print("🎫 Исследуем информацию о бронях...")
        
        try:
            # Ищем ссылки или разделы, связанные с бронями
            booking_selectors = [
                'a[href*="booking"]',
                'a[href*="ticket"]',
                'a[href*="trip"]',
                'a:has-text("Мои поездки")',
                'a:has-text("Билеты")',
                'a:has-text("Брони")',
                '.bookings',
                '.tickets',
                '.my-trips'
            ]
            
            booking_link = None
            for selector in booking_selectors:
                try:
                    booking_link = await page.wait_for_selector(selector, timeout=3000)
                    if booking_link:
                        print(f"🎯 Найдена ссылка на брони: {selector}")
                        await booking_link.click()
                        await page.wait_for_load_state('networkidle')
                        break
                except:
                    continue
            
            if not booking_link:
                print("🔍 Ищем брони на текущей странице профиля...")
            
            # Делаем скриншот страницы с бронями
            await page.screenshot(path="bookings_page.png", full_page=True)
            print("📸 Скриншот страницы с бронями сохранен как bookings_page.png")
            
            # Извлекаем информацию о бронях
            bookings_info = await self.extract_bookings_info(page)
            print("📋 Информация о бронях:")
            if bookings_info:
                for i, booking in enumerate(bookings_info, 1):
                    print(f"   Бронь #{i}:")
                    for key, value in booking.items():
                        print(f"     {key}: {value}")
            else:
                print("   Брони не найдены или список пуст")
            
        except Exception as e:
            print(f"⚠️ Ошибка при исследовании броней: {e}")
            await page.screenshot(path="bookings_error.png")
    
    async def extract_bookings_info(self, page):
        """Извлечение информации о бронях"""
        bookings = []
        
        try:
            # Ищем контейнеры с бронями
            booking_containers = [
                '.booking-item',
                '.ticket-item',
                '.trip-item',
                '[data-testid="booking"]',
                '.booking',
                '.ticket',
                '.reservation'
            ]
            
            for container_selector in booking_containers:
                try:
                    containers = await page.query_selector_all(container_selector)
                    if containers:
                        print(f"📦 Найдено {len(containers)} броней в контейнере: {container_selector}")
                        
                        for container in containers:
                            booking_data = {}
                            
                            # Извлекаем текст из контейнера
                            try:
                                text_content = await container.text_content()
                                if text_content:
                                    booking_data['Содержимое'] = text_content.strip()
                                
                                # Ищем специфичные поля
                                field_selectors = {
                                    'Дата': ['.date', '.trip-date', '[data-testid="date"]'],
                                    'Маршрут': ['.route', '.trip-route', '[data-testid="route"]'],
                                    'Статус': ['.status', '.booking-status', '[data-testid="status"]'],
                                    'Цена': ['.price', '.cost', '[data-testid="price"]']
                                }
                                
                                for field_name, selectors in field_selectors.items():
                                    for selector in selectors:
                                        try:
                                            field_element = await container.query_selector(selector)
                                            if field_element:
                                                field_text = await field_element.text_content()
                                                if field_text and field_text.strip():
                                                    booking_data[field_name] = field_text.strip()
                                                    break
                                        except:
                                            continue
                                
                                if booking_data:
                                    bookings.append(booking_data)
                                    
                            except Exception as e:
                                print(f"⚠️ Ошибка при извлечении данных брони: {e}")
                        
                        if bookings:
                            break
                            
                except:
                    continue
            
            # Если не найдены специфичные контейнеры, ищем общую информацию
            if not bookings:
                print("🔍 Ищем общую информацию о бронях...")
                general_info = {}
                
                # Ищем любые упоминания о бронях/билетах
                text_content = await page.text_content('body')
                if 'бронь' in text_content.lower() or 'билет' in text_content.lower():
                    general_info['Общая информация'] = "Страница содержит информацию о бронях/билетах"
                    bookings.append(general_info)
                
        except Exception as e:
            print(f"⚠️ Ошибка при извлечении информации о бронях: {e}")
        
        return bookings
    
    async def explore_site_functionality(self, page):
        """Исследование общего функционала сайта"""
        print("🔍 Исследуем общий функционал сайта...")
        
        try:
            # Исследуем навигацию
            await self.explore_navigation(page)
            
            # Исследуем поиск маршрутов
            await self.explore_route_search(page)
            
            # Общий обзор функций
            await self.general_site_overview(page)
            
        except Exception as e:
            print(f"⚠️ Ошибка при исследовании функционала: {e}")
            await page.screenshot(path="functionality_error.png")
    
    async def explore_navigation(self, page):
        """Исследование навигации сайта"""
        print("🧭 Исследуем навигацию сайта...")
        
        try:
            # Ищем элементы навигации
            nav_selectors = [
                'nav a',
                '.navigation a',
                '.menu a',
                '.navbar a',
                'header a',
                '.nav-link'
            ]
            
            navigation_links = []
            for selector in nav_selectors:
                try:
                    links = await page.query_selector_all(selector)
                    if links:
                        for link in links:
                            href = await link.get_attribute('href')
                            text = await link.text_content()
                            if href and text and text.strip():
                                navigation_links.append({
                                    'text': text.strip(),
                                    'href': href,
                                    'selector': selector
                                })
                        break
                except:
                    continue
            
            if navigation_links:
                print("📋 Найденные элементы навигации:")
                for link in navigation_links[:10]:  # Показываем первые 10
                    print(f"   {link['text']} -> {link['href']}")
            else:
                print("❌ Элементы навигации не найдены")
                
        except Exception as e:
            print(f"⚠️ Ошибка при исследовании навигации: {e}")
    
    async def explore_route_search(self, page):
        """Исследование функции поиска маршрутов"""
        print("🚌 Исследуем поиск маршрутов...")
        
        try:
            # Переходим на главную для поиска
            await page.goto(self.base_url, wait_until='networkidle')
            
            # Ищем поля поиска маршрутов
            search_selectors = {
                'Откуда': [
                    'input[placeholder*="Откуда"]',
                    'input[name*="from"]',
                    'input[id*="from"]',
                    '.from-input'
                ],
                'Куда': [
                    'input[placeholder*="Куда"]',
                    'input[name*="to"]',
                    'input[id*="to"]',
                    '.to-input'
                ],
                'Дата': [
                    'input[type="date"]',
                    'input[placeholder*="Дата"]',
                    'input[name*="date"]',
                    '.date-input'
                ]
            }
            
            search_form_found = False
            for field_name, selectors in search_selectors.items():
                for selector in selectors:
                    try:
                        field = await page.query_selector(selector)
                        if field:
                            print(f"✅ Найдено поле '{field_name}': {selector}")
                            search_form_found = True
                            break
                    except:
                        continue
                if search_form_found:
                    break
            
            if search_form_found:
                print("🎯 Форма поиска маршрутов найдена!")
                # Делаем скриншот формы поиска
                await page.screenshot(path="search_form.png", full_page=True)
                print("📸 Скриншот формы поиска сохранен как search_form.png")
            else:
                print("❌ Форма поиска маршрутов не найдена")
                
        except Exception as e:
            print(f"⚠️ Ошибка при исследовании поиска маршрутов: {e}")
    
    async def general_site_overview(self, page):
        """Общий обзор сайта"""
        print("📊 Общий обзор функционала сайта...")
        
        try:
            # Собираем общую статистику
            overview = {
                'URL': page.url,
                'Заголовок': await page.title(),
                'Количество ссылок': len(await page.query_selector_all('a')),
                'Количество форм': len(await page.query_selector_all('form')),
                'Количество кнопок': len(await page.query_selector_all('button')),
                'Количество изображений': len(await page.query_selector_all('img'))
            }
            
            print("📋 Статистика сайта:")
            for key, value in overview.items():
                print(f"   {key}: {value}")
            
            # Финальный скриншот
            await page.screenshot(path="final_overview.png", full_page=True)
            print("📸 Финальный скриншот сохранен как final_overview.png")
            
        except Exception as e:
            print(f"⚠️ Ошибка при создании обзора: {e}")

async def main():
    """Главная функция"""
    explorer = MarshaExplorer()
    await explorer.run()

if __name__ == "__main__":
    print("🎭 Запуск исследователя сайта маршруточки...")
    print("=" * 50)
    asyncio.run(main())
