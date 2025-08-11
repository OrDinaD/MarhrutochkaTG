#!/usr/bin/env python3
"""
Улучшенная система авторизации для сайта маршруточки
Основана на анализе реального сайта через Playwright
"""

import asyncio
import logging
import requests
import json
import os
from typing import Dict, Optional, Any, List
from urllib.parse import urlencode
from datetime import datetime, timedelta
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """Профиль пользователя"""
    name: str
    surname: str
    patronymic: str
    email: str
    phone: str
    birth_date: str
    passport_series: str = ""
    card_number: str = ""
    status: str = ""


@dataclass
class UserBooking:
    """Бронирование пользователя"""
    booking_id: str
    route: str
    date: str
    departure_time: str
    ticket_number: str
    price: str
    status: str


@dataclass
class RouteInfo:
    """Информация о маршруте"""
    route_id: str
    from_location: str
    to_location: str
    departure_time: str
    arrival_time: str
    price: str
    available_seats: int
    bus_info: str = ""
    duration: str = ""


@dataclass
class BookingRequest:
    """Запрос на бронирование"""
    route_id: str
    passenger_count: int
    passenger_name: str
    passenger_phone: str
    departure_date: str


class ImprovedWebAuth:
    """Улучшенная система веб-авторизации"""
    
    def __init__(self):
        self.base_url = "https://xn--90aiim0b.xn--80aa3agllaqi6bg.xn--90ais"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        self.authenticated = False
        self.user_profile: Optional[UserProfile] = None
        self.phone = None
        self.csrf_token = None
        
    def _extract_csrf_token(self, html_content: str) -> Optional[str]:
        """Извлекает CSRF токен из HTML"""
        patterns = [
            r'<input[^>]+name="_token"[^>]+value="([^"]+)"',
            r'<input[^>]+value="([^"]+)"[^>]+name="_token"',
            r'name="[_]?token"\s+value="([^"]+)"',
            r'<meta name="csrf-token" content="([^"]+)"',
            r'window\.Laravel\s*=\s*[^}]*"csrfToken":"([^"]+)"',
            r'_token["\']?\s*[:=]\s*["\']([^"\']+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                token = match.group(1)
                logger.debug(f"CSRF токен найден с паттерном: {pattern[:50]}...")
                return token
        
        logger.warning("CSRF токен не найден")
        return None
    
    def get_main_page(self) -> bool:
        """Получает главную страницу и извлекает необходимые данные"""
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            # Извлекаем CSRF токен
            self.csrf_token = self._extract_csrf_token(response.text)
            if self.csrf_token:
                logger.info(f"CSRF токен извлечен: {self.csrf_token[:20]}...")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка получения главной страницы: {e}")
            return False
    
    def login(self, phone: str, password: str) -> bool:
        """
        Авторизация на сайте
        
        Args:
            phone: Номер телефона (например: +375299605390 или 299605390)
            password: Пароль
            
        Returns:
            bool: True если авторизация успешна
        """
        try:
            # Получаем главную страницу
            if not self.get_main_page():
                return False
            
            # Нормализуем номер телефона
            clean_phone = re.sub(r'[^\d]', '', phone)
            if clean_phone.startswith('375'):
                clean_phone = clean_phone[3:]  # Убираем код страны
            
            # Формат должен быть точно как ожидает сайт
            formatted_phone = f"+375 ({clean_phone[:2]}) {clean_phone[2:5]}-{clean_phone[5:7]}-{clean_phone[7:]}"
            
            logger.info(f"Попытка авторизации для номера: {formatted_phone}")
            
            # Подготавливаем данные для авторизации точно как в форме
            login_data = {
                'phone': formatted_phone,  # Полный формат как в браузере
                'password': password,
                'remember': '1'  # Чекбокс "Запомнить"
            }
            
            # Добавляем CSRF токен если есть
            if self.csrf_token:
                login_data['_token'] = self.csrf_token
            
            # Отправляем запрос авторизации
            login_url = f"{self.base_url}/auth/login"
            
            # Устанавливаем специальные заголовки для POST запроса
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.base_url,
                'Origin': self.base_url,
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Encoding': 'gzip, deflate, br'
            }
            
            # Обновляем заголовки сессии
            old_headers = self.session.headers.copy()
            self.session.headers.update(headers)
            
            logger.info(f"Отправляем данные: {login_data}")
            response = self.session.post(login_url, data=login_data, allow_redirects=False)
            
            # Восстанавливаем заголовки
            self.session.headers = old_headers
            
            logger.info(f"Статус ответа авторизации: {response.status_code}")
            logger.info(f"URL ответа: {response.url}")
            logger.info(f"Заголовки ответа: {dict(response.headers)}")
            
            # Проверяем ответ
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    logger.info(f"JSON ответ: {json_response}")
                    
                    # Проверяем, есть ли в ответе признаки успеха
                    if json_response.get('success') or json_response.get('status') == 'success':
                        # Дополнительная проверка через профиль
                        if self._check_authentication():
                            self.authenticated = True
                            self.phone = formatted_phone
                            logger.info("Авторизация успешна!")
                            return True
                except json.JSONDecodeError:
                    # Если не JSON, проверяем через профиль
                    pass
            
            # Проверяем редирект
            if response.status_code in [302, 301]:
                location = response.headers.get('Location', '')
                logger.info(f"Редирект на: {location}")
                
                # Если редирект на главную или профиль, это может быть успех
                if '/' in location or 'profile' in location:
                    if self._check_authentication():
                        self.authenticated = True
                        self.phone = formatted_phone
                        logger.info("Авторизация успешна!")
                        return True
            
            # Проверяем успешность авторизации
            if self._check_authentication():
                self.authenticated = True
                self.phone = formatted_phone
                logger.info("Авторизация успешна!")
                return True
            else:
                logger.warning("Авторизация не удалась")
                logger.info(f"Содержимое ответа: {response.text[:500]}...")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}", exc_info=True)
            return False
    
    def _check_authentication(self) -> bool:
        """Проверяет, авторизован ли пользователь"""
        try:
            # Пытаемся получить доступ к профилю
            profile_url = f"{self.base_url}/profile"
            response = self.session.get(profile_url)
            
            # Ищем признаки успешной авторизации
            success_indicators = [
                'Личный кабинет',
                'Персональные данные',
                'Мои заказы',
                'Выйти',
                'profile/tickets'
            ]
            
            for indicator in success_indicators:
                if indicator in response.text:
                    logger.info(f"Найден индикатор авторизации: {indicator}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка проверки авторизации: {e}")
            return False
    
    def get_user_profile(self) -> Optional[UserProfile]:
        """Получает профиль пользователя"""
        if not self.authenticated:
            logger.warning("Пользователь не авторизован")
            return None
            
        try:
            profile_url = f"{self.base_url}/profile"
            response = self.session.get(profile_url)
            response.raise_for_status()
            
            logger.info(f"Получен ответ на /profile, статус: {response.status_code}")
            logger.info(f"Размер ответа: {len(response.text)} символов")
            
            # Логируем часть ответа для отладки
            logger.debug(f"Начало HTML: {response.text[:500]}")
            
            # Парсим профиль из HTML
            profile = self._parse_profile_from_html(response.text)
            if profile:
                self.user_profile = profile
                logger.info(f"Профиль загружен: {profile.name} {profile.surname}")
            else:
                logger.warning("Не удалось распарсить профиль из HTML")
            
            return profile
            
        except Exception as e:
            logger.error(f"Ошибка получения профиля: {e}")
            return None
    
    def _parse_profile_from_html(self, html: str) -> Optional[UserProfile]:
        """Парсит профиль пользователя из HTML"""
        try:
            extracted = {}
            
            # Паттерны для поиска данных в input полях с value атрибутами
            patterns = {
                'name': [
                    r'name="first_name"[^>]*value="([^"]*)"',
                    r'id="userName"[^>]*value="([^"]*)"'
                ],
                'surname': [
                    r'name="last_name"[^>]*value="([^"]*)"',
                    r'id="LastName"[^>]*value="([^"]*)"'
                ],
                'patronymic': [
                    r'name="middle_name"[^>]*value="([^"]*)"',
                    r'id="MiddleName"[^>]*value="([^"]*)"'
                ],
                'email': [
                    r'name="email"[^>]*value="([^"]*)"',
                    r'id="email"[^>]*value="([^"]*)"'
                ],
                'phone': [
                    r'name="phone"[^>]*value="([^"]*)"',
                    r'placeholder="Телефон"[^>]*value="([^"]*)"'
                ],
                'birth_date': [
                    r'name="birth_date"[^>]*value="([^"]*)"',
                    r'name="birthday"[^>]*value="([^"]*)"'
                ]
            }
            
            # Ищем данные по паттернам
            for field, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                    if match and match.group(1).strip():
                        value = match.group(1).strip()
                        if value and value not in ['+', '']:  # Исключаем пустые значения и одинокий +
                            extracted[field] = value
                            logger.debug(f"Найдено {field}: '{value}' паттерном: {pattern}")
                            break
            
            # Если телефон все еще не найден или содержит только +, используем сохраненный номер
            if (not extracted.get('phone') or extracted.get('phone') == '+') and self.phone:
                extracted['phone'] = self.phone
            
            # Логируем все найденные данные
            logger.info(f"Извлеченные данные профиля: {extracted}")
            
            # Если удалось извлечь основные данные
            if any(extracted.get(field) for field in ['name', 'surname', 'email']):
                return UserProfile(
                    name=extracted.get('name', ''),
                    surname=extracted.get('surname', ''),
                    patronymic=extracted.get('patronymic', ''),
                    email=extracted.get('email', ''),
                    phone=extracted.get('phone', ''),
                    birth_date=extracted.get('birth_date', ''),
                    passport_series=extracted.get('passport_series', ''),
                    card_number=extracted.get('card_number', '')
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка парсинга профиля: {e}")
            return None
    
    def get_user_bookings(self, booking_type: str = "upcoming") -> List[UserBooking]:
        """
        Получает бронирования пользователя
        
        Args:
            booking_type: "upcoming", "completed", "cancelled"
        """
        if not self.authenticated:
            logger.warning("Пользователь не авторизован")
            return []
            
        try:
            # URL для разных типов бронирований
            booking_urls = {
                "upcoming": f"{self.base_url}/profile/tickets?upcoming",
                "completed": f"{self.base_url}/profile/tickets?done", 
                "cancelled": f"{self.base_url}/profile/tickets?cancelled"
            }
            
            url = booking_urls.get(booking_type, booking_urls["upcoming"])
            response = self.session.get(url)
            response.raise_for_status()
            
            # Парсим бронирования из HTML
            bookings = self._parse_bookings_from_html(response.text)
            logger.info(f"Найдено {len(bookings)} бронирований типа {booking_type}")
            
            return bookings
            
        except Exception as e:
            logger.error(f"Ошибка получения бронирований: {e}")
            return []
    
    def _parse_bookings_from_html(self, html: str) -> List[UserBooking]:
        """Парсит бронирования из HTML таблицы"""
        try:
            bookings = []
            
            # Ищем таблицу с бронированиями
            table_pattern = r'<table[^>]*>.*?</table>'
            table_match = re.search(table_pattern, html, re.DOTALL | re.IGNORECASE)
            
            if not table_match:
                return bookings
            
            table_html = table_match.group(0)
            
            # Ищем строки таблицы (исключая заголовок)
            row_pattern = r'<tr[^>]*>(.*?)</tr>'
            rows = re.findall(row_pattern, table_html, re.DOTALL | re.IGNORECASE)
            
            for row_html in rows:
                # Пропускаем заголовок и пустые строки
                if 'Маршрут' in row_html or 'Поездки не найдены' in row_html:
                    continue
                
                # Извлекаем ячейки
                cell_pattern = r'<td[^>]*>(.*?)</td>'
                cells = re.findall(cell_pattern, row_html, re.DOTALL | re.IGNORECASE)
                
                if len(cells) >= 6:
                    # Очищаем HTML теги из ячеек
                    cleaned_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
                    
                    booking = UserBooking(
                        booking_id=cleaned_cells[0],
                        route=cleaned_cells[1],
                        date=cleaned_cells[2],
                        departure_time=cleaned_cells[3],
                        ticket_number=cleaned_cells[4],
                        price=cleaned_cells[5],
                        status="active"
                    )
                    bookings.append(booking)
            
            return bookings
            
        except Exception as e:
            logger.error(f"Ошибка парсинга бронирований: {e}")
            return []
    
    def search_routes(self, from_location: str, to_location: str, date: str) -> List[RouteInfo]:
        """
        Поиск маршрутов
        
        Args:
            from_location: Откуда (например: "Минск")
            to_location: Куда (например: "Островец")
            date: Дата в формате YYYY-MM-DD
            
        Returns:
            List[RouteInfo]: Список найденных маршрутов
        """
        try:
            # URL для поиска маршрутов
            search_url = f"{self.base_url}/search"
            
            # Подготавливаем данные для поиска
            search_data = {
                'from': from_location,
                'to': to_location,
                'date': date,
                'passengers': 1
            }
            
            # Добавляем CSRF токен если есть
            if self.csrf_token:
                search_data['_token'] = self.csrf_token
            
            logger.info(f"Ищу маршруты: {from_location} → {to_location} на {date}")
            
            # Отправляем запрос поиска
            response = self.session.post(search_url, data=search_data)
            response.raise_for_status()
            
            logger.info(f"Получен ответ поиска, статус: {response.status_code}")
            
            # Парсим результаты поиска
            routes = self._parse_routes_from_html(response.text)
            logger.info(f"Найдено маршрутов: {len(routes)}")
            
            return routes
            
        except Exception as e:
            logger.error(f"Ошибка поиска маршрутов: {e}")
            return []
    
    def _parse_routes_from_html(self, html: str) -> List[RouteInfo]:
        """Парсит маршруты из HTML результатов поиска"""
        try:
            routes = []
            
            # Ищем таблицу с маршрутами или карточки
            # Примерный паттерн для строк таблицы маршрутов
            route_pattern = r'<tr[^>]*class="[^"]*route[^"]*"[^>]*>(.*?)</tr>'
            route_matches = re.findall(route_pattern, html, re.DOTALL | re.IGNORECASE)
            
            if not route_matches:
                # Альтернативный поиск - по div блокам
                route_pattern = r'<div[^>]*class="[^"]*route-item[^"]*"[^>]*>(.*?)</div>'
                route_matches = re.findall(route_pattern, html, re.DOTALL | re.IGNORECASE)
            
            for match in route_matches:
                route = self._parse_single_route(match)
                if route:
                    routes.append(route)
            
            # Если не нашли через паттерны, попробуем более простой подход
            if not routes:
                routes = self._parse_routes_simple(html)
            
            return routes
            
        except Exception as e:
            logger.error(f"Ошибка парсинга маршрутов: {e}")
            return []
    
    def _parse_single_route(self, route_html: str) -> Optional[RouteInfo]:
        """Парсит один маршрут из HTML"""
        try:
            # Извлекаем данные маршрута
            route_data = {}
            
            # ID маршрута
            route_id_match = re.search(r'data-route-id="([^"]+)"', route_html)
            if route_id_match:
                route_data['route_id'] = route_id_match.group(1)
            else:
                # Генерируем временный ID
                route_data['route_id'] = f"route_{hash(route_html) % 10000}"
            
            # Время отправления
            time_patterns = [
                r'<td[^>]*class="[^"]*time[^"]*"[^>]*>([^<]+)</td>',
                r'<span[^>]*class="[^"]*departure[^"]*"[^>]*>([^<]+)</span>',
                r'(\d{2}:\d{2})'
            ]
            
            for pattern in time_patterns:
                time_match = re.search(pattern, route_html)
                if time_match:
                    route_data['departure_time'] = time_match.group(1).strip()
                    break
            
            # Цена
            price_patterns = [
                r'<td[^>]*class="[^"]*price[^"]*"[^>]*>([^<]+)</td>',
                r'<span[^>]*class="[^"]*price[^"]*"[^>]*>([^<]+)</span>',
                r'(\d+[.,]\d+)\s*руб'
            ]
            
            for pattern in price_patterns:
                price_match = re.search(pattern, route_html)
                if price_match:
                    route_data['price'] = price_match.group(1).strip()
                    break
            
            # Количество свободных мест
            seats_patterns = [
                r'<td[^>]*class="[^"]*seats[^"]*"[^>]*>([^<]+)</td>',
                r'(\d+)\s*мест'
            ]
            
            for pattern in seats_patterns:
                seats_match = re.search(pattern, route_html)
                if seats_match:
                    try:
                        route_data['available_seats'] = int(re.search(r'\d+', seats_match.group(1)).group())
                    except:
                        route_data['available_seats'] = 0
                    break
            
            # Если нашли основные данные, создаем маршрут
            if route_data.get('departure_time') and route_data.get('price'):
                return RouteInfo(
                    route_id=route_data.get('route_id', ''),
                    from_location="",  # Будет заполнено из поискового запроса
                    to_location="",    # Будет заполнено из поискового запроса
                    departure_time=route_data.get('departure_time', ''),
                    arrival_time=route_data.get('arrival_time', ''),
                    price=route_data.get('price', ''),
                    available_seats=route_data.get('available_seats', 0),
                    bus_info=route_data.get('bus_info', ''),
                    duration=route_data.get('duration', '')
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка парсинга маршрута: {e}")
            return None
    
    def _parse_routes_simple(self, html: str) -> List[RouteInfo]:
        """Упрощенный парсинг маршрутов"""
        try:
            routes = []
            
            # Ищем все время отправления
            time_pattern = r'(\d{2}:\d{2})'
            times = re.findall(time_pattern, html)
            
            # Ищем все цены
            price_pattern = r'(\d+[.,]\d+)\s*руб'
            prices = re.findall(price_pattern, html)
            
            # Создаем маршруты из найденных данных
            for i, (time, price) in enumerate(zip(times, prices)):
                route = RouteInfo(
                    route_id=f"simple_route_{i}",
                    from_location="",
                    to_location="",
                    departure_time=time,
                    arrival_time="",
                    price=price,
                    available_seats=1,  # Предполагаем что места есть
                    bus_info="",
                    duration=""
                )
                routes.append(route)
            
            return routes
            
        except Exception as e:
            logger.error(f"Ошибка упрощенного парсинга: {e}")
            return []
    
    def book_ticket(self, booking_request: BookingRequest) -> Optional[UserBooking]:
        """
        Бронирование билета
        
        Args:
            booking_request: Данные для бронирования
            
        Returns:
            UserBooking: Данные о созданном бронировании или None
        """
        if not self.authenticated:
            logger.warning("Пользователь не авторизован для бронирования")
            return None
            
        try:
            # URL для бронирования
            booking_url = f"{self.base_url}/booking"
            
            # Подготавливаем данные для бронирования
            booking_data = {
                'route_id': booking_request.route_id,
                'passenger_count': booking_request.passenger_count,
                'passenger_name': booking_request.passenger_name,
                'passenger_phone': booking_request.passenger_phone,
                'departure_date': booking_request.departure_date
            }
            
            # Добавляем CSRF токен
            if self.csrf_token:
                booking_data['_token'] = self.csrf_token
            
            logger.info(f"Создаю бронирование для маршрута {booking_request.route_id}")
            
            # Отправляем запрос бронирования
            response = self.session.post(booking_url, data=booking_data)
            response.raise_for_status()
            
            logger.info(f"Ответ на бронирование, статус: {response.status_code}")
            
            # Парсим результат бронирования
            booking = self._parse_booking_result(response.text, booking_request)
            
            if booking:
                logger.info(f"Бронирование создано: {booking.booking_id}")
                return booking
            else:
                logger.warning("Не удалось создать бронирование")
                return None
            
        except Exception as e:
            logger.error(f"Ошибка бронирования: {e}")
            return None
    
    def _parse_booking_result(self, html: str, request: BookingRequest) -> Optional[UserBooking]:
        """Парсит результат бронирования"""
        try:
            # Ищем ID бронирования
            booking_id_patterns = [
                r'booking[_-]?id["\s:]+([^"\s<>,]+)',
                r'номер[^:]*:\s*([^<\s]+)',
                r'заказ[^:]*:\s*([^<\s]+)'
            ]
            
            booking_id = None
            for pattern in booking_id_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    booking_id = match.group(1).strip()
                    break
            
            # Если не нашли ID, генерируем временный
            if not booking_id:
                booking_id = f"booking_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Ищем номер билета
            ticket_patterns = [
                r'ticket[_-]?number["\s:]+([^"\s<>,]+)',
                r'билет[^:]*:\s*([^<\s]+)'
            ]
            
            ticket_number = ""
            for pattern in ticket_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    ticket_number = match.group(1).strip()
                    break
            
            # Создаем объект бронирования
            booking = UserBooking(
                booking_id=booking_id,
                route=f"{request.passenger_name}",  # Временно используем имя пассажира
                date=request.departure_date,
                departure_time="",  # Будет заполнено позже
                ticket_number=ticket_number,
                price="",
                status="confirmed"
            )
            
            return booking
            
        except Exception as e:
            logger.error(f"Ошибка парсинга результата бронирования: {e}")
            return None
    
    def logout(self) -> bool:
        """Выход из аккаунта"""
        try:
            logout_url = f"{self.base_url}/auth/logout"
            response = self.session.get(logout_url)
            
            self.authenticated = False
            self.user_profile = None
            self.phone = None
            self.csrf_token = None
            
            logger.info("Выход из аккаунта выполнен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка выхода из аккаунта: {e}")
            return False
    
    def save_session(self, filepath: str) -> bool:
        """Сохраняет сессию в файл"""
        try:
            session_data = {
                'cookies': dict(self.session.cookies),
                'authenticated': self.authenticated,
                'phone': self.phone,
                'csrf_token': self.csrf_token,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Сессия сохранена в {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения сессии: {e}")
            return False
    
    def load_session(self, filepath: str) -> bool:
        """Загружает сессию из файла"""
        try:
            if not os.path.exists(filepath):
                return False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Проверяем, не устарела ли сессия (24 часа)
            timestamp = datetime.fromisoformat(session_data.get('timestamp', ''))
            if datetime.now() - timestamp > timedelta(hours=24):
                logger.info("Сессия устарела")
                return False
            
            # Восстанавливаем cookies
            for name, value in session_data.get('cookies', {}).items():
                self.session.cookies.set(name, value)
            
            self.authenticated = session_data.get('authenticated', False)
            self.phone = session_data.get('phone')
            self.csrf_token = session_data.get('csrf_token')
            
            # Проверяем, что сессия все еще активна
            if self.authenticated and self._check_authentication():
                logger.info("Сессия успешно восстановлена")
                return True
            else:
                logger.info("Сессия недействительна")
                self.authenticated = False
                return False
                
        except Exception as e:
            logger.error(f"Ошибка загрузки сессии: {e}")
            return False


def test_auth():
    """Тестирование авторизации"""
    
    # Используем данные из переменных окружения или значения по умолчанию
    phone = os.getenv('DEFAULT_PHONE', '+375299605390')
    password = os.getenv('DEFAULT_PASSWORD', 'Zxcvbnm,1')
    
    auth = ImprovedWebAuth()
    
    print("Тестирование авторизации...")
    
    # Тестируем авторизацию
    success = auth.login(phone, password)
    print(f"Авторизация: {'✅ Успешно' if success else '❌ Неудачно'}")
    
    if success:
        # Получаем профиль
        profile = auth.get_user_profile()
        if profile:
            print(f"Профиль: {profile.name} {profile.surname}")
            print(f"Email: {profile.email}")
            print(f"Телефон: {profile.phone}")
        
        # Получаем бронирования
        bookings = auth.get_user_bookings("upcoming")
        print(f"Предстоящие бронирования: {len(bookings)}")
        
        for booking in bookings:
            print(f"  - {booking.route} ({booking.date} {booking.departure_time})")
        
        # Сохраняем сессию
        session_file = "test_session.json"
        auth.save_session(session_file)
        print(f"Сессия сохранена в {session_file}")


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_auth()
