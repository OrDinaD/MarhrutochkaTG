#!/usr/bin/env python3
"""
Исследование процесса бронирования маршрутов через Playwright
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Добавляем src в путь
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class BookingExplorer:
    def __init__(self):
        self.page = None
        self.browser = None
        self.context = None
        
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)  # С GUI для исследования
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def explore_login_process(self):
        """Исследуем процесс входа в аккаунт"""
        print("🔐 Исследуем процесс входа...")
        
        try:
            # Переходим на главную страницу
            await self.page.goto("https://билет.маршруточка.бел/")
            await self.page.wait_for_load_state('networkidle')
            
            # Ищем кнопку входа
            login_buttons = await self.page.query_selector_all("a, button")
            for button in login_buttons:
                text = await button.inner_text() if button else ""
                if any(word in text.lower() for word in ['вход', 'войти', 'login', 'личный']):
                    print(f"   Найдена кнопка входа: '{text}'")
                    await button.click()
                    break
            
            await self.page.wait_for_timeout(2000)
            
            # Ищем поля для ввода
            phone_field = await self.page.query_selector("input[type='tel'], input[name*='phone'], input[placeholder*='телефон']")
            password_field = await self.page.query_selector("input[type='password']")
            
            if phone_field and password_field:
                print("   ✅ Найдены поля для ввода телефона и пароля")
                
                # Вводим тестовые данные
                phone = os.getenv('DEFAULT_PHONE', '+375299605390')
                password = os.getenv('DEFAULT_PASSWORD', 'Zxcvbnm,1')
                
                await phone_field.fill(phone)
                await password_field.fill(password)
                
                # Ищем кнопку отправки
                submit_button = await self.page.query_selector("button[type='submit'], input[type='submit']")
                if submit_button:
                    await submit_button.click()
                    await self.page.wait_for_timeout(3000)
                    
                    # Проверяем успешность входа
                    current_url = self.page.url
                    print(f"   URL после входа: {current_url}")
                    
                    # Ищем элементы профиля
                    profile_elements = await self.page.query_selector_all("*")
                    for element in profile_elements[:20]:  # Проверяем первые 20 элементов
                        text = await element.inner_text() if element else ""
                        if any(word in text.lower() for word in ['профиль', 'мои билеты', 'выход']):
                            print(f"   Найден элемент профиля: '{text}'")
                            
            else:
                print("   ❌ Не найдены поля для входа")
                
        except Exception as e:
            print(f"   ❌ Ошибка при исследовании входа: {e}")

    async def explore_booking_process(self):
        """Исследуем процесс бронирования"""
        print("\n🎫 Исследуем процесс бронирования...")
        
        try:
            # Переходим на страницу поиска
            await self.page.goto("https://билет.маршруточка.бел/")
            await self.page.wait_for_load_state('networkidle')
            
            # Ищем поля для выбора маршрута
            from_field = await self.page.query_selector("select, input")
            date_field = await self.page.query_selector("input[type='date'], input[placeholder*='дата']")
            
            if from_field and date_field:
                # Устанавливаем завтрашнюю дату
                tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                await date_field.fill(tomorrow)
                
                # Ищем кнопку поиска
                search_button = await self.page.query_selector("button")
                if search_button:
                    await search_button.click()
                    await self.page.wait_for_timeout(3000)
                    
                    # Анализируем результаты поиска
                    routes = await self.page.query_selector_all(".route-item, .trip-item, tr")
                    print(f"   Найдено потенциальных рейсов: {len(routes)}")
                    
                    for i, route in enumerate(routes[:5]):  # Анализируем первые 5
                        try:
                            route_text = await route.inner_text()
                            if any(word in route_text for word in [':', 'минск', 'островец']):
                                print(f"   Рейс {i+1}: {route_text[:100]}...")
                                
                                # Ищем кнопки бронирования
                                book_buttons = await route.query_selector_all("button, a")
                                for button in book_buttons:
                                    button_text = await button.inner_text()
                                    if any(word in button_text.lower() for word in ['забронировать', 'купить', 'выбрать']):
                                        print(f"     Найдена кнопка: '{button_text}'")
                                        
                                        # Кликаем на кнопку бронирования
                                        await button.click()
                                        await self.page.wait_for_timeout(2000)
                                        
                                        # Анализируем форму бронирования
                                        await self.analyze_booking_form()
                                        break
                                break
                        except Exception as e:
                            continue
            
        except Exception as e:
            print(f"   ❌ Ошибка при исследовании бронирования: {e}")

    async def analyze_booking_form(self):
        """Анализируем форму бронирования"""
        print("\n📋 Анализируем форму бронирования...")
        
        try:
            # Ждем загрузки формы
            await self.page.wait_for_timeout(2000)
            
            # Ищем поля формы бронирования
            form_fields = await self.page.query_selector_all("input, select, textarea")
            print(f"   Найдено полей в форме: {len(form_fields)}")
            
            for field in form_fields:
                try:
                    field_type = await field.get_attribute('type')
                    field_name = await field.get_attribute('name')
                    field_placeholder = await field.get_attribute('placeholder')
                    
                    print(f"     Поле: type='{field_type}', name='{field_name}', placeholder='{field_placeholder}'")
                except:
                    continue
            
            # Ищем селектор количества пассажиров
            passenger_selectors = await self.page.query_selector_all("select, input[type='number']")
            for selector in passenger_selectors:
                try:
                    selector_name = await selector.get_attribute('name')
                    if selector_name and any(word in selector_name.lower() for word in ['passenger', 'count', 'количество']):
                        print(f"     Найден селектор пассажиров: {selector_name}")
                        
                        # Получаем опции
                        if await selector.get_attribute('tagName') == 'SELECT':
                            options = await selector.query_selector_all('option')
                            print(f"       Доступные опции: {len(options)}")
                            for option in options:
                                value = await option.get_attribute('value')
                                text = await option.inner_text()
                                print(f"         {value}: {text}")
                except:
                    continue
            
            # Ищем информацию о доступных местах
            seat_info = await self.page.query_selector_all("*")
            for element in seat_info:
                try:
                    text = await element.inner_text()
                    if any(word in text.lower() for word in ['мест', 'свободн', 'доступн']):
                        print(f"     Информация о местах: {text}")
                except:
                    continue
                    
            # Ищем кнопку подтверждения бронирования
            confirm_buttons = await self.page.query_selector_all("button")
            for button in confirm_buttons:
                try:
                    button_text = await button.inner_text()
                    if any(word in button_text.lower() for word in ['подтвердить', 'забронировать', 'оплатить']):
                        print(f"     Найдена кнопка подтверждения: '{button_text}'")
                except:
                    continue
                    
        except Exception as e:
            print(f"   ❌ Ошибка при анализе формы: {e}")

    async def explore_existing_bookings(self):
        """Исследуем как отображаются существующие брони"""
        print("\n📊 Исследуем отображение существующих броней...")
        
        try:
            # Ищем раздел "Мои билеты" или похожий
            navigation_links = await self.page.query_selector_all("a, button")
            
            for link in navigation_links:
                try:
                    text = await link.inner_text()
                    if any(word in text.lower() for word in ['мои билеты', 'брони', 'заказы', 'tickets']):
                        print(f"   Найдена ссылка на брони: '{text}'")
                        await link.click()
                        await self.page.wait_for_timeout(3000)
                        
                        # Анализируем структуру страницы с бронями
                        booking_elements = await self.page.query_selector_all("*")
                        for element in booking_elements[:50]:  # Первые 50 элементов
                            try:
                                element_text = await element.inner_text()
                                if any(word in element_text.lower() for word in ['№', 'дата', 'маршрут', 'статус']):
                                    print(f"     Элемент брони: {element_text}")
                            except:
                                continue
                        break
                except:
                    continue
                    
        except Exception as e:
            print(f"   ❌ Ошибка при исследовании броней: {e}")

async def main():
    """Основная функция исследования"""
    print("🔍 Начинаем исследование процесса бронирования")
    print("=" * 50)
    
    async with BookingExplorer() as explorer:
        await explorer.explore_login_process()
        await explorer.explore_booking_process()  
        await explorer.explore_existing_bookings()
        
        # Даем время для ручного исследования
        print("\n⏰ Окно браузера останется открытым на 30 секунд для ручного исследования...")
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
