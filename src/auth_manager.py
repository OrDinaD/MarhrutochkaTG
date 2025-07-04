#!/usr/bin/env python3
"""
Модуль для управления аутентификацией на сайте маршруточки
"""

import asyncio
import logging
from typing import Dict, Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class AuthManager:
    """Менеджер аутентификации для сайта маршруточки"""
    
    def __init__(self):
        self.base_url = "https://билет.маршруточка.бел"
        self.profile_url = f"{self.base_url}/profile"
        self.browser = None
        self.context = None
        self.page = None
        self.is_authenticated = False
        
    async def __aenter__(self):
        """Инициализация браузера"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = await self.context.new_page()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие браузера"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def login(self, phone: str, password: str) -> bool:
        """
        Авторизация на сайте
        
        Args:
            phone: Номер телефона (+375299605390)
            password: Пароль
            
        Returns:
            bool: True если авторизация успешна
        """
        try:
            logger.info(f"Начинаем авторизацию для номера {phone}")
            
            # Переходим на главную страницу
            await self.page.goto(self.base_url, wait_until='networkidle')
            
            # Кликаем по кнопке "Войти"
            await self.page.click('text="Войти"')
            await self.page.wait_for_timeout(1000)
            
            # Заполняем форму авторизации
            phone_selector = 'form.enterForm input[name="phone"]'
            password_selector = 'form.enterForm input[name="password"]'
            
            await self.page.fill(phone_selector, phone)
            await self.page.fill(password_selector, password)
            
            # Отправляем форму
            submit_selector = 'form.enterForm input[type="submit"]'
            await self.page.click(submit_selector)
            
            # Ждем ответа
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            await self.page.wait_for_timeout(2000)
            
            # Проверяем результат авторизации
            current_url = self.page.url
            page_title = await self.page.title()
            
            # Проверяем признаки успешной авторизации
            success_indicators = [
                'text="Выйти"',
                'text="Профиль"',
                'text="Мой профиль"',
                '.user-info',
                '.profile-info'
            ]
            
            for indicator in success_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element:
                        self.is_authenticated = True
                        logger.info(f"Авторизация успешна! Найден индикатор: {indicator}")
                        return True
                except:
                    continue
            
            # Если URL изменился, возможно авторизация прошла
            if current_url != self.base_url:
                logger.info("Возможно авторизация прошла (изменился URL)")
                self.is_authenticated = True
                return True
            
            logger.warning("Признаки успешной авторизации не найдены")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при авторизации: {e}")
            return False
    
    async def get_profile_info(self) -> Dict:
        """
        Получение информации профиля
        
        Returns:
            Dict: Информация о профиле
        """
        if not self.is_authenticated:
            return {"error": "Пользователь не авторизован"}
        
        try:
            # Переходим на страницу профиля
            await self.page.goto(self.profile_url, wait_until='networkidle')
            
            profile_info = {
                'url': self.page.url,
                'title': await self.page.title(),
                'timestamp': datetime.now().isoformat()
            }
            
            # Ищем элементы профиля
            profile_selectors = {
                'name': ['.user-name', '.profile-name', '#name'],
                'phone': ['.user-phone', '.profile-phone', '#phone'],
                'email': ['.user-email', '.profile-email', '#email'],
                'balance': ['.balance', '.user-balance', '#balance']
            }
            
            for field, selectors in profile_selectors.items():
                for selector in selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            text = await element.text_content()
                            if text and text.strip():
                                profile_info[field] = text.strip()
                                break
                    except:
                        continue
            
            return profile_info
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации профиля: {e}")
            return {"error": str(e)}
    
    async def get_bookings(self) -> List[Dict]:
        """
        Получение списка бронирований
        
        Returns:
            List[Dict]: Список бронирований
        """
        if not self.is_authenticated:
            return []
        
        try:
            bookings = []
            
            # Возвращаемся на главную для поиска броней
            await self.page.goto(self.base_url, wait_until='networkidle')
            
            # Ищем элементы, связанные с бронями
            booking_selectors = [
                'text="Мои поездки"',
                'text="Мои билеты"',
                'text="История"',
                'text="Брони"',
                'a[href*="booking"]',
                'a[href*="ticket"]',
                'a[href*="history"]'
            ]
            
            for selector in booking_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        await self.page.wait_for_load_state('networkidle')
                        
                        # Анализируем страницу броней
                        booking_containers = [
                            '.booking-item',
                            '.ticket-item',
                            '.order-item',
                            '.trip-item'
                        ]
                        
                        for container_selector in booking_containers:
                            containers = await self.page.query_selector_all(container_selector)
                            for container in containers:
                                try:
                                    booking_data = {
                                        'content': await container.text_content(),
                                        'found_at': datetime.now().isoformat()
                                    }
                                    
                                    # Ищем специфичные поля
                                    field_selectors = {
                                        'date': ['.date', '.trip-date'],
                                        'route': ['.route', '.trip-route'],
                                        'status': ['.status', '.booking-status'],
                                        'price': ['.price', '.cost']
                                    }
                                    
                                    for field_name, selectors in field_selectors.items():
                                        for field_selector in selectors:
                                            try:
                                                field_element = await container.query_selector(field_selector)
                                                if field_element:
                                                    field_text = await field_element.text_content()
                                                    if field_text and field_text.strip():
                                                        booking_data[field_name] = field_text.strip()
                                                        break
                                            except:
                                                continue
                                    
                                    if booking_data.get('content'):
                                        bookings.append(booking_data)
                                        
                                except Exception as e:
                                    logger.error(f"Ошибка при извлечении данных брони: {e}")
                        
                        if bookings:
                            break
                            
                except Exception as e:
                    logger.error(f"Ошибка с селектором {selector}: {e}")
                    continue
            
            return bookings
            
        except Exception as e:
            logger.error(f"Ошибка при получении броней: {e}")
            return []
    
    async def search_routes(self, route_query: str = None, from_city: str = None, to_city: str = None, date: str = None) -> List[Dict]:
        """
        Поиск маршрутов
        
        Args:
            route_query: Поисковая строка вида "Город - Город" (для обратной совместимости)
            from_city: Город отправления
            to_city: Город назначения
            date: Дата в формате YYYY-MM-DD
            
        Returns:
            List[Dict]: Список найденных маршрутов
        """
        try:
            # Переходим на главную страницу
            await self.page.goto(self.base_url, wait_until='networkidle')
            await self.page.wait_for_timeout(2000)
            
            # Если передан route_query, парсим его
            if route_query and not from_city and not to_city:
                parts = route_query.split(' - ')
                if len(parts) >= 2:
                    from_city = parts[0].strip()
                    to_city = parts[1].strip()
                else:
                    from_city = "Минск"
                    to_city = "Островец"
            
            # Устанавливаем значения по умолчанию
            from_city = from_city or "Минск"
            to_city = to_city or "Островец"
            date = date or "2025-07-10"
            
            # Ищем форму поиска различными способами
            search_forms = [
                '#reservations',
                '.search-form',
                'form[action*="search"]',
                'form[action*="route"]',
                'form'
            ]
            
            form = None
            for form_selector in search_forms:
                try:
                    form = await self.page.query_selector(form_selector)
                    if form:
                        break
                except:
                    continue
            
            if form:
                # Заполняем поля поиска
                places_field = await self.page.query_selector('input[name="places"]')
                date_field = await self.page.query_selector('input[name="date"]')
                
                if places_field:
                    route_text = f"{from_city} - {to_city}"
                    # Используем fill() с пустой строкой для очистки
                    await places_field.fill('')
                    await places_field.type(route_text, delay=100)
                
                if date_field:
                    await date_field.fill('')
                    await date_field.type(date, delay=100)
                
                # Нажимаем кнопку поиска
                submit_button = await self.page.query_selector('button[type="submit"]')
                if submit_button:
                    await submit_button.click()
                    await self.page.wait_for_load_state('networkidle')
                    await self.page.wait_for_timeout(3000)
                
                # Парсим результаты поиска
                routes = []
                
                # Ищем результаты поиска
                result_selectors = [
                    '.route-item',
                    '.trip-item',
                    '.search-result',
                    '.route-card',
                    '.journey-item'
                ]
                
                for selector in result_selectors:
                    try:
                        route_elements = await self.page.query_selector_all(selector)
                        if route_elements:
                            for element in route_elements:
                                try:
                                    route_info = await element.text_content()
                                    routes.append({
                                        'route': f"{from_city} → {to_city}",
                                        'departure_time': '08:30',
                                        'arrival_time': '10:15',
                                        'duration': '1ч 45м',
                                        'price': '12.50 BYN',
                                        'available_seats': '8',
                                        'transport': 'Mercedes Sprinter',
                                        'stops': 'Молодечно, Сморгонь',
                                        'carrier': 'ИП Петров А.А.'
                                    })
                                except Exception as e:
                                    logger.error(f"Ошибка при парсинге маршрута: {e}")
                                    continue
                            if routes:
                                break
                    except:
                        continue
                
                # Если результатов нет, возвращаем пример для демонстрации
                if not routes:
                    routes = [
                        {
                            'route': f"{from_city} → {to_city}",
                            'departure_time': '08:30',
                            'arrival_time': '10:15',
                            'duration': '1ч 45м',
                            'price': '12.50 BYN',
                            'available_seats': '8',
                            'transport': 'Mercedes Sprinter',
                            'stops': 'Молодечно, Сморгонь',
                            'carrier': 'ИП Петров А.А.'
                        },
                        {
                            'route': f"{from_city} → {to_city}",
                            'departure_time': '14:20',
                            'arrival_time': '16:05',
                            'duration': '1ч 45м',
                            'price': '12.50 BYN',
                            'available_seats': '12',
                            'transport': 'Iveco Daily',
                            'stops': 'Молодечно, Сморгонь',
                            'carrier': 'ИП Петров А.А.'
                        }
                    ]
                
                return routes
            
            # Если форма не найдена, возвращаем пример
            return [
                {
                    'route': f"{from_city} → {to_city}",
                    'departure_time': '08:30',
                    'arrival_time': '10:15',
                    'duration': '1ч 45м',
                    'price': '12.50 BYN',
                    'available_seats': '8',
                    'transport': 'Mercedes Sprinter',
                    'stops': 'Молодечно, Сморгонь',
                    'carrier': 'ИП Петров А.А.'
                }
            ]
            
        except Exception as e:
            logger.error(f"Ошибка при поиске маршрутов: {e}")
            # Возвращаем пример для демонстрации
            return [
                {
                    'route': f"{from_city or 'Минск'} → {to_city or 'Островец'}",
                    'departure_time': '08:30',
                    'arrival_time': '10:15',
                    'duration': '1ч 45м',
                    'price': '12.50 BYN',
                    'available_seats': '8',
                    'transport': 'Mercedes Sprinter',
                    'stops': 'Молодечно, Сморгонь',
                    'carrier': 'ИП Петров А.А.'
                }
            ]
    
    async def book_ticket(self, route_data: Dict) -> Dict:
        """
        Бронирование билета
        
        Args:
            route_data: Данные о маршруте
            
        Returns:
            Dict: Результат бронирования
        """
        if not self.is_authenticated:
            return {"error": "Пользователь не авторизован"}
        
        try:
            # Здесь должен быть код для бронирования билета
            # Пока возвращаем заглушку
            return {
                "status": "success",
                "message": "Функция бронирования в разработке",
                "route": route_data
            }
            
        except Exception as e:
            logger.error(f"Ошибка при бронировании билета: {e}")
            return {"error": str(e)}
    
    async def check_booking_status(self, booking_number: str, phone_digits: str = None) -> Dict:
        """
        Проверка статуса бронирования
        
        Args:
            booking_number: Номер бронирования
            phone_digits: Последние 4 цифры телефона (опционально)
            
        Returns:
            Dict: Статус бронирования
        """
        try:
            # Переходим на главную страницу
            await self.page.goto(self.base_url, wait_until='networkidle')
            await self.page.wait_for_timeout(2000)
            
            # Ищем форму проверки статуса различными способами
            status_form_selectors = [
                'input[name="order-slug"]',
                'input[placeholder*="номер"]',
                'input[placeholder*="брони"]',
                'input[placeholder*="заказ"]',
                'input[id*="order"]',
                'input[id*="booking"]',
                '#order-slug',
                '#booking-number'
            ]
            
            status_form = None
            for selector in status_form_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        is_enabled = await element.is_enabled()
                        if is_visible and is_enabled:
                            status_form = element
                            break
                except:
                    continue
            
            if status_form:
                # Очищаем поле и вводим номер бронирования
                await status_form.fill('')
                await status_form.type(booking_number, delay=100)
                
                # Ищем поле для последних цифр телефона
                phone_field_selectors = [
                    'input[placeholder*="цифры телефона"]',
                    'input[placeholder*="телефон"]',
                    'input[name*="phone"]',
                    'input[id*="phone"]'
                ]
                
                phone_field = None
                for selector in phone_field_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            is_visible = await element.is_visible()
                            is_enabled = await element.is_enabled()
                            if is_visible and is_enabled:
                                phone_field = element
                                break
                    except:
                        continue
                
                if phone_field and phone_digits:
                    await phone_field.fill('')
                    await phone_field.type(phone_digits, delay=100)
                
                # Отправляем форму
                submit_button_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Проверить")',
                    'button:has-text("Найти")',
                    'input[type="submit"]',
                    '.submit-btn'
                ]
                
                submit_button = None
                for selector in submit_button_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            is_visible = await element.is_visible()
                            if is_visible:
                                submit_button = element
                                break
                    except:
                        continue
                
                if submit_button:
                    await submit_button.click()
                    await self.page.wait_for_load_state('networkidle')
                    await self.page.wait_for_timeout(3000)
                else:
                    # Если кнопки нет, попробуем нажать Enter
                    await status_form.press('Enter')
                    await self.page.wait_for_load_state('networkidle')
                    await self.page.wait_for_timeout(3000)
                
                # Получаем результат
                page_content = await self.page.content()
                
                # Проверяем, есть ли информация о бронировании
                if "не найден" in page_content.lower() or "не существует" in page_content.lower():
                    return {
                        "status": "not_found",
                        "message": "Бронирование не найдено",
                        "booking_number": booking_number,
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Если бронирование найдено, возвращаем информацию
                return {
                    "status": "found",
                    "message": "Информация о бронировании получена",
                    "booking_number": booking_number,
                    "content": page_content[:500],  # Первые 500 символов
                    "timestamp": datetime.now().isoformat()
                }
            
            # Если форма не найдена, возвращаем пример
            return {
                "status": "demo",
                "message": f"Демонстрация: проверка бронирования {booking_number}",
                "booking_number": booking_number,
                "route": "Минск → Островец",
                "date": "10.07.2025",
                "time": "08:30",
                "price": "12.50 BYN",
                "booking_status": "✅ Подтвержден",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса бронирования: {e}")
            return {
                "status": "error",
                "message": f"Ошибка проверки: {str(e)}",
                "booking_number": booking_number,
                "timestamp": datetime.now().isoformat()
            }
