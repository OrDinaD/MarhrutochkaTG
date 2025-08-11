#!/usr/bin/env python3
"""
Исправленная система авторизации для билеты.маршруточка.бел
"""

import logging
import requests
import time
from typing import Dict, List, Optional, Tuple, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import re

# Настройка логирования
logger = logging.getLogger(__name__)


class RequestsAuthManager:
    """Менеджер аутентификации через requests.Session"""
    
    def __init__(self):
        # Альтернативные URL'ы для подключения
        self.possible_urls = [
            "https://marshrutochka.by",
            "https://bilet.marshrutochka.by", 
            "https://www.marshrutochka.by",
            "http://marshrutochka.by",
        ]
        self.base_url = None
        self.session = requests.Session()
        self.authenticated = False
        self.profile_data = {}
        self.phone = ""
        
        # Настройка сессии
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,be;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })
        
        self.timeout = 10
        
        # Ищем рабочий URL
        self._find_working_url()
        
        logger.info(f"Инициализирован RequestsAuthManager с URL: {self.base_url}")
    
    def _find_working_url(self):
        """Поиск рабочего URL сайта"""
        for url in self.possible_urls:
            try:
                logger.debug(f"Проверяем URL: {url}")
                response = self.session.get(url, timeout=5, allow_redirects=True)
                
                if response.status_code == 200:
                    # Проверяем, что это нужный сайт
                    content = response.text.lower()
                    if any(keyword in content for keyword in ['маршруточка', 'билет', 'marshrutochka']):
                        self.base_url = url
                        logger.info(f"Найден рабочий URL: {url}")
                        return
                        
            except Exception as e:
                logger.debug(f"Ошибка проверки {url}: {e}")
                continue
        
        # Если ничего не найдено, используем первый URL как fallback
        self.base_url = self.possible_urls[0]
        logger.warning(f"Рабочий URL не найден, используем fallback: {self.base_url}")
    
    def validate_phone_number(self, phone: str) -> Tuple[bool, str]:
        """Валидация номера телефона"""
        # Очищаем номер от лишних символов
        clean_phone = re.sub(r'[^\d+]', '', phone)
        
        # Проверяем формат белорусского номера
        patterns = [
            r'^\+375(25|29|33|44)\d{7}$',  # +375XXXXXXXXX
            r'^375(25|29|33|44)\d{7}$',    # 375XXXXXXXXX
            r'^(25|29|33|44)\d{7}$'        # XXXXXXXXX
        ]
        
        for pattern in patterns:
            if re.match(pattern, clean_phone):
                # Нормализуем к формату +375XXXXXXXXX
                if clean_phone.startswith('+375'):
                    return True, clean_phone
                elif clean_phone.startswith('375'):
                    return True, '+' + clean_phone
                else:
                    return True, '+375' + clean_phone
        
        return False, "Некорректный формат номера. Используйте: +375XXXXXXXXX"
    
    def login(self, username: str, password: str) -> bool:
        """Выполнить вход с улучшенной валидацией"""
        try:
            # Валидируем номер телефона
            phone_valid, phone_message = self.validate_phone_number(username)
            if not phone_valid:
                logger.error(f"Некорректный номер телефона: {phone_message}")
                return False
            
            # Нормализуем номер телефона
            normalized_phone = phone_message
            self.phone = normalized_phone
            
            logger.info(f"Попытка входа с номером: {normalized_phone}")
            
            if not self.base_url:
                logger.error("Рабочий URL не найден")
                return False
            
            # Получаем страницу входа
            try:
                response = self.session.get(self.base_url, timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                csrf_token = self._extract_csrf_token(soup)
            except Exception as e:
                logger.warning(f"Ошибка получения главной страницы: {e}")
                csrf_token = None
            
            # Подготавливаем данные для входа
            login_data = {
                'phone': normalized_phone,
                'password': password,
            }
            
            # Добавляем CSRF токен, если найден
            if csrf_token:
                login_data['_token'] = csrf_token
                logger.info("CSRF токен добавлен к данным входа")
            
            # Пытаемся различные URL для входа
            login_endpoints = [
                "/login",
                "/auth/login", 
                "/user/login",
                "/api/login",
                "/signin"
            ]
            
            for endpoint in login_endpoints:
                try:
                    login_url = urljoin(self.base_url, endpoint)
                    logger.info(f"Попытка входа через: {login_url}")
                    
                    headers = {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': self.base_url,
                        'Origin': self.base_url
                    }
                    
                    response = self.session.post(
                        login_url,
                        data=login_data,
                        headers=headers,
                        timeout=self.timeout,
                        allow_redirects=True
                    )
                    
                    # Проверяем результат
                    if response.status_code == 200:
                        # Проверяем содержимое ответа
                        content = response.text.lower()
                        
                        # Индикаторы успешного входа
                        success_indicators = [
                            'profile', 'cabinet', 'личный', 'профиль',
                            'welcome', 'dashboard', 'logout', 'выйти',
                            'успешно'
                        ]
                        
                        # Индикаторы ошибки
                        error_indicators = [
                            'error', 'ошибка', 'неверный', 'неправильно',
                            'invalid', 'incorrect', 'wrong'
                        ]
                        
                        has_success = any(indicator in content for indicator in success_indicators)
                        has_error = any(indicator in content for indicator in error_indicators)
                        
                        if has_success and not has_error:
                            logger.info("Успешный вход обнаружен")
                            self.authenticated = True
                            self._fetch_profile_data()
                            return True
                        
                        elif has_error:
                            logger.warning(f"Обнаружена ошибка входа в ответе от {endpoint}")
                            continue
                        
                        # Если неясно, проверяем cookies
                        if len(self.session.cookies) > 0:
                            cookie_names = [cookie.name.lower() for cookie in self.session.cookies]
                            auth_cookies = ['session', 'auth', 'token', 'login', 'user']
                            
                            if any(auth_name in ' '.join(cookie_names) for auth_name in auth_cookies):
                                logger.info("Найдены cookies авторизации")
                                self.authenticated = True
                                self._fetch_profile_data()
                                return True
                    
                    elif response.status_code in [302, 301]:
                        # Редирект может означать успешный вход
                        location = response.headers.get('Location', '')
                        if any(indicator in location.lower() for indicator in ['profile', 'cabinet', 'dashboard']):
                            logger.info("Успешный вход (редирект в профиль)")
                            self.authenticated = True
                            self._fetch_profile_data()
                            return True
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Ошибка запроса к {endpoint}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Неожиданная ошибка при входе через {endpoint}: {e}")
                    continue
            
            logger.error("Все попытки входа неуспешны")
            return False
            
        except Exception as e:
            logger.error(f"Критическая ошибка при входе: {e}")
            return False
    
    def _extract_csrf_token(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение CSRF токена"""
        selectors = [
            'input[name="_token"]',
            'input[name="csrf_token"]', 
            'input[name="authenticity_token"]',
            'meta[name="csrf-token"]',
            'meta[name="_token"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                token = element.get('value') or element.get('content')
                if token:
                    return token
        
        return None
    
    def _fetch_profile_data(self):
        """Получение данных профиля"""
        try:
            profile_endpoints = [
                "/profile",
                "/cabinet", 
                "/user/profile",
                "/account",
                "/personal"
            ]
            
            for endpoint in profile_endpoints:
                try:
                    profile_url = urljoin(self.base_url, endpoint)
                    response = self.session.get(profile_url, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Пытаемся извлечь данные профиля
                        profile_data = self._parse_profile_page(soup)
                        if profile_data:
                            self.profile_data = profile_data
                            logger.info("Данные профиля успешно получены")
                            return
                            
                except Exception as e:
                    logger.debug(f"Ошибка получения профиля с {endpoint}: {e}")
                    continue
            
            # Если не удалось получить профиль, создаем базовые данные
            self.profile_data = {
                'phone': self.phone,
                'authenticated': True,
                'login_time': time.time()
            }
            logger.info("Созданы базовые данные профиля")
            
        except Exception as e:
            logger.error(f"Ошибка получения данных профиля: {e}")
            self.profile_data = {'phone': self.phone, 'error': str(e)}
    
    def _parse_profile_page(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Парсинг страницы профиля"""
        profile_data = {}
        
        try:
            # Различные селекторы для данных профиля
            field_selectors = {
                'name': [
                    'input[name="name"]', '.profile-name', '.user-name',
                    'span:contains("Имя")', 'label:contains("Имя")'
                ],
                'email': [
                    'input[name="email"]', '.profile-email', '.user-email',
                    'span:contains("Email")', 'label:contains("Email")'
                ],
                'phone': [
                    'input[name="phone"]', '.profile-phone', '.user-phone',
                    'span:contains("Телефон")', 'label:contains("Телефон")'
                ],
                'balance': [
                    '.balance', '.user-balance', '.account-balance',
                    'span:contains("Баланс")', 'label:contains("Баланс")'
                ]
            }
            
            for field, selectors in field_selectors.items():
                for selector in selectors:
                    try:
                        element = soup.select_one(selector)
                        if element:
                            value = element.get('value') or element.get_text(strip=True)
                            if value and len(value) > 0:
                                profile_data[field] = value
                                break
                    except:
                        continue
            
            # Добавляем телефон из сохраненного значения
            if 'phone' not in profile_data and self.phone:
                profile_data['phone'] = self.phone
            
            profile_data['authenticated'] = True
            profile_data['fetch_time'] = time.time()
            
            return profile_data if profile_data else None
            
        except Exception as e:
            logger.error(f"Ошибка парсинга профиля: {e}")
            return None
    
    def get_profile(self) -> Dict[str, Any]:
        """Получить данные профиля"""
        if not self.authenticated:
            logger.warning("Не аутентифицирован")
            return {
                'success': False,
                'error': 'Не аутентифицирован',
                'data': {}
            }
        
        return {
            'success': True,
            'data': self.profile_data
        }
    
    def get_tickets(self) -> List[Dict[str, Any]]:
        """Получить билеты пользователя"""
        if not self.authenticated:
            logger.warning("Не аутентифицирован для получения билетов")
            return []
        
        try:
            # Пытаемся получить билеты
            tickets_endpoints = [
                "/tickets",
                "/bookings",
                "/reservations", 
                "/my-tickets",
                "/user/tickets"
            ]
            
            for endpoint in tickets_endpoints:
                try:
                    tickets_url = urljoin(self.base_url, endpoint)
                    response = self.session.get(tickets_url, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        tickets = self._parse_tickets_page(soup)
                        if tickets:
                            return tickets
                            
                except Exception as e:
                    logger.warning(f"Ошибка получения билетов с {endpoint}: {e}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Ошибка получения билетов: {e}")
            return []
    
    def _parse_tickets_page(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Парсинг страницы с билетами"""
        tickets = []
        
        try:
            # Ищем билеты по различным селекторам
            ticket_selectors = [
                '.ticket', '.booking', '.reservation',
                '.ticket-item', '.booking-item'
            ]
            
            for selector in ticket_selectors:
                ticket_elements = soup.select(selector)
                if ticket_elements:
                    for element in ticket_elements:
                        ticket_data = self._extract_ticket_data(element)
                        if ticket_data:
                            tickets.append(ticket_data)
                    break
            
            return tickets[:20]  # Ограничиваем количество
            
        except Exception as e:
            logger.error(f"Ошибка парсинга билетов: {e}")
            return []
    
    def _extract_ticket_data(self, element) -> Optional[Dict[str, Any]]:
        """Извлечение данных одного билета"""
        try:
            ticket_data = {}
            
            # Извлекаем основные данные
            text_content = element.get_text(strip=True)
            
            # Ищем номер билета
            ticket_number_match = re.search(r'№\s*(\d+)', text_content)
            if ticket_number_match:
                ticket_data['ticket_number'] = ticket_number_match.group(1)
            
            # Ищем дату
            date_match = re.search(r'(\d{1,2}[.-]\d{1,2}[.-]\d{2,4})', text_content)
            if date_match:
                ticket_data['date'] = date_match.group(1)
            
            # Ищем маршрут
            route_patterns = [
                r'Минск\s*[→-]\s*Островец',
                r'Островец\s*[→-]\s*Минск'
            ]
            
            for pattern in route_patterns:
                route_match = re.search(pattern, text_content, re.IGNORECASE)
                if route_match:
                    ticket_data['route'] = route_match.group(0)
                    break
            
            # Ищем статус
            if any(word in text_content.lower() for word in ['активн', 'действ']):
                ticket_data['status'] = 'active'
            elif any(word in text_content.lower() for word in ['отмен', 'аннул']):
                ticket_data['status'] = 'cancelled'
            else:
                ticket_data['status'] = 'unknown'
            
            return ticket_data if ticket_data else None
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных билета: {e}")
            return None
    
    @property
    def is_authenticated(self) -> bool:
        """Проверить аутентификацию"""
        return self.authenticated
