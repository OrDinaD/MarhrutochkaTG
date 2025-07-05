#!/usr/bin/env python3
"""
Requests-based authentication and data extraction for bilyet.marshrut.by
Попытка обойти проблемы с сессиями через requests.Session
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestsAuthManager:
    """Менеджер аутентификации через requests.Session"""
    
    def __init__(self, base_url: str = "https://xn--90aiim0b.xn--80aa3agllaqi6bg.xn--90ais"):
        self.base_url = base_url
        self.session = requests.Session()
        self.authenticated = False
        self.profile_data = {}
        
        # Настройка сессии
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        # Настройка для работы с SSL
        self.session.verify = True
        
        # Настройка таймаутов
        self.timeout = 15
        
        logger.info(f"Инициализирован RequestsAuthManager для {base_url}")
    
    def get_login_page(self) -> Tuple[bool, str]:
        """Получить страницу входа и извлечь CSRF токен"""
        try:
            # Получаем главную страницу, где есть форма входа
            url = self.base_url
            logger.info(f"Получаем главную страницу с формой входа: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Сохраняем cookies
            logger.info(f"Получены cookies: {dict(self.session.cookies)}")
            
            # Извлекаем CSRF токен
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = self._extract_csrf_token(soup)
            
            if csrf_token:
                logger.info(f"Найден CSRF токен: {csrf_token[:10]}...")
                return True, csrf_token
            else:
                logger.warning("CSRF токен не найден")
                return False, ""
                
        except Exception as e:
            logger.error(f"Ошибка при получении страницы входа: {e}")
            return False, ""
    
    def _extract_csrf_token(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечь CSRF токен из формы"""
        # Ищем токен по различным селекторам
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
        
        # Ищем токен в скриптах
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Ищем различные паттерны токенов
                patterns = [
                    r'_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    r'csrf_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    r'authenticity_token["\']?\s*[:=]\s*["\']([^"\']+)["\']'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, script.string, re.IGNORECASE)
                    if match:
                        return match.group(1)
        
        return None
    
    def login(self, username: str, password: str) -> bool:
        """Выполнить вход"""
        try:
            # Получаем страницу входа
            success, csrf_token = self.get_login_page()
            if not success:
                logger.error("Не удалось получить страницу входа")
                return False
            
            # Подготавливаем данные для входа
            login_data = {
                'phone': username,  # Используем phone вместо username
                'password': password,
            }
            
            # Добавляем CSRF токен, если найден
            if csrf_token:
                login_data['_token'] = csrf_token
            
            # Отправляем POST запрос на правильный URL
            login_url = urljoin(self.base_url, "/auth/login")
            logger.info(f"Отправляем данные входа на {login_url}")
            
            # Добавляем заголовки для AJAX запроса
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
                allow_redirects=False  # Не следуем редиректам автоматически
            )
            
            logger.info(f"Статус ответа: {response.status_code}")
            logger.info(f"Итоговый URL: {response.url}")
            logger.info(f"Cookies после входа: {dict(self.session.cookies)}")
            
            # Проверяем успешность входа
            if self._check_authentication(response):
                self.authenticated = True
                logger.info("Успешный вход!")
                return True
            else:
                logger.error("Неудачный вход")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при входе: {e}")
            return False
    
    def _check_authentication(self, response: requests.Response) -> bool:
        """Проверить успешность аутентификации"""
        # Проверяем JSON ответ
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                json_response = response.json()
                logger.info(f"JSON ответ: {json_response}")
                
                # Проверяем статус в JSON
                if json_response.get('result') == 'success':
                    logger.info("Получен успешный JSON ответ")
                    
                    # Если есть redirect URL, переходим по нему
                    redirect_url = json_response.get('redirect')
                    if redirect_url:
                        logger.info(f"Выполняем редирект на: {redirect_url}")
                        redirect_response = self.session.get(redirect_url, timeout=self.timeout)
                        logger.info(f"Статус после редиректа: {redirect_response.status_code}")
                        logger.info(f"URL после редиректа: {redirect_response.url}")
                    
                    return True
                elif json_response.get('result') == 'error':
                    logger.error(f"Ошибка входа: {json_response.get('message', 'неизвестная ошибка')}")
                    return False
        except Exception as e:
            logger.debug(f"Не JSON ответ или ошибка парсинга: {e}")
        
        # Проверяем статус код
        if response.status_code != 200:
            logger.warning(f"Неожиданный статус код: {response.status_code}")
        
        # Проверяем URL - успешный вход обычно перенаправляет на главную или профиль
        if 'login' in response.url:
            logger.warning("Остались на странице входа")
            return False
        
        # Проверяем содержимое страницы
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем признаки успешного входа
        success_indicators = [
            'logout', 'profile', 'dashboard', 'account',
            'выход', 'профиль', 'личный кабинет'
        ]
        
        page_text = response.text.lower()
        for indicator in success_indicators:
            if indicator in page_text:
                logger.info(f"Найден индикатор успешного входа: {indicator}")
                return True
        
        # Ищем ошибки входа
        error_indicators = [
            'invalid', 'incorrect', 'wrong', 'error',
            'неверный', 'неправильный', 'ошибка'
        ]
        
        for indicator in error_indicators:
            if indicator in page_text:
                logger.warning(f"Найден индикатор ошибки: {indicator}")
                return False
        
        # Проверяем cookies
        if len(self.session.cookies) > 0:
            logger.info("Получены cookies - вероятно, вход успешен")
            return True
        
        logger.warning("Не удалось определить статус входа")
        return False
    
    def get_profile_info(self) -> Dict[str, Any]:
        """Получить информацию профиля"""
        if not self.authenticated:
            logger.warning("Не аутентифицирован")
            return {
                'success': False,
                'error': 'Не аутентифицирован',
                'data': {}
            }
        
        try:
            # Пробуем различные URL профиля
            profile_urls = [
                "/profile",
                "/account",
                "/user",
                "/dashboard",
                "/personal",
                "/my-account"
            ]
            
            for url_path in profile_urls:
                url = urljoin(self.base_url, url_path)
                logger.info(f"Попытка получения профиля: {url}")
                
                response = self.session.get(url, timeout=self.timeout)
                logger.info(f"Статус ответа: {response.status_code}")
                
                if response.status_code == 200:
                    profile_data = self._extract_profile_data(response)
                    if profile_data:
                        self.profile_data = profile_data
                        return {
                            'success': True,
                            'data': profile_data,
                            'url': url
                        }
                
                # Небольшая задержка между запросами
                time.sleep(0.5)
            
            logger.warning("Не удалось получить данные профиля")
            return {
                'success': False,
                'error': 'Не удалось получить данные профиля',
                'data': {}
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении профиля: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    def _extract_profile_data(self, response: requests.Response) -> Dict[str, Any]:
        """Извлечь данные профиля из ответа"""
        soup = BeautifulSoup(response.text, 'html.parser')
        profile_data = {}
        
        # Ищем все input поля со значениями (наиболее точный способ для этого сайта)
        inputs_with_values = soup.find_all('input', value=True)
        for input_elem in inputs_with_values:
            name = input_elem.get('name', '')
            value = input_elem.get('value', '')
            input_type = input_elem.get('type', 'text')
            
            # Пропускаем служебные поля
            if input_type in ['hidden', 'submit', 'button', 'checkbox'] or not value or not name:
                continue
            
            # Маппинг полей
            field_mapping = {
                'first_name': 'first_name',
                'middle_name': 'middle_name', 
                'last_name': 'last_name',
                'email': 'email',
                'phone': 'phone',
                'birth_day': 'birth_date',
                'card': 'card_number',
                'passport': 'passport'
            }
            
            if name in field_mapping:
                profile_data[field_mapping[name]] = value
                logger.info(f"Найдено поле {name}: {value}")
        
        # Формируем полное имя
        if 'first_name' in profile_data or 'last_name' in profile_data:
            name_parts = []
            if 'last_name' in profile_data:
                name_parts.append(profile_data['last_name'])
            if 'first_name' in profile_data:
                name_parts.append(profile_data['first_name'])
            if 'middle_name' in profile_data:
                name_parts.append(profile_data['middle_name'])
            
            if name_parts:
                profile_data['full_name'] = ' '.join(name_parts)
        
        # Альтернативные селекторы, если input поля не найдены
        if not profile_data:
            selectors = {
                'full_name': [
                    '.profile-name', '.user-name', '.full-name',
                    '.name', '[data-field="name"]', '.личное-имя'
                ],
                'email': [
                    '.profile-email', '.user-email', '.email',
                    '[data-field="email"]', '[type="email"]'
                ],
                'phone': [
                    '.profile-phone', '.user-phone', '.phone',
                    '[data-field="phone"]', '[type="tel"]'
                ],
                'birth_date': [
                    '.profile-birthdate', '.user-birthdate', '.birth-date',
                    '[data-field="birthdate"]', '[type="date"]'
                ]
            }
            
            for field, field_selectors in selectors.items():
                for selector in field_selectors:
                    element = soup.select_one(selector)
                    if element:
                        # Пробуем получить текст или значение
                        value = element.get('value') or element.get_text(strip=True)
                        if value:
                            profile_data[field] = value
                            logger.info(f"Найдено поле {field}: {value}")
                            break
        
        return profile_data
    
    def get_bookings(self) -> Dict[str, Any]:
        """Получить список бронирований"""
        if not self.authenticated:
            logger.warning("Не аутентифицирован")
            return {
                'success': False,
                'error': 'Не аутентифицирован',
                'bookings': []
            }
        
        try:
            # Пробуем различные URL для бронирований
            booking_urls = [
                "/profile/tickets?upcoming",  # Найденный URL
                "/profile/tickets",
                "/bookings",
                "/orders",
                "/tickets",
                "/reservations",
                "/my-bookings",
                "/my-orders",
                "/profile/bookings",
                "/account/bookings"
            ]
            
            for url_path in booking_urls:
                url = urljoin(self.base_url, url_path)
                logger.info(f"Попытка получения бронирований: {url}")
                
                response = self.session.get(url, timeout=self.timeout)
                logger.info(f"Статус ответа: {response.status_code}")
                
                if response.status_code == 200:
                    bookings = self._extract_bookings_data(response)
                    if bookings:
                        return {
                            'success': True,
                            'bookings': bookings,
                            'url': url
                        }
                
                # Небольшая задержка между запросами
                time.sleep(0.5)
            
            logger.warning("Не удалось получить данные бронирований")
            return {
                'success': False,
                'error': 'Не удалось получить данные бронирований',
                'bookings': []
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении бронирований: {e}")
            return {
                'success': False,
                'error': str(e),
                'bookings': []
            }
    
    def _extract_bookings_data(self, response: requests.Response) -> List[Dict[str, Any]]:
        """Извлечь данные бронирований из ответа"""
        soup = BeautifulSoup(response.text, 'html.parser')
        bookings = []
        
        # Ищем таблицы с бронированиями
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 1:  # Есть заголовок и данные
                # Пробуем извлечь данные из таблицы
                header_row = rows[0]
                headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
                
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= len(headers):
                        booking = {}
                        for i, header in enumerate(headers):
                            if i < len(cells):
                                value = cells[i].get_text(strip=True)
                                booking[header] = value
                        
                        if booking:
                            bookings.append(booking)
        
        # Ищем карточки или блоки бронирований
        booking_selectors = [
            '.booking', '.order', '.ticket', '.reservation',
            '.booking-card', '.order-card', '.ticket-card'
        ]
        
        for selector in booking_selectors:
            elements = soup.select(selector)
            for element in elements:
                booking = self._extract_booking_from_element(element)
                if booking:
                    bookings.append(booking)
        
        return bookings
    
    def _extract_booking_from_element(self, element) -> Dict[str, Any]:
        """Извлечь данные бронирования из элемента"""
        booking = {}
        
        # Ищем различные поля
        text = element.get_text(strip=True)
        
        # Ищем номер бронирования
        number_patterns = [
            r'№\s*(\d+)',
            r'#\s*(\d+)',
            r'booking\s*(\d+)',
            r'order\s*(\d+)'
        ]
        
        for pattern in number_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                booking['number'] = match.group(1)
                break
        
        # Ищем дату
        date_patterns = [
            r'(\d{1,2}\.\d{1,2}\.\d{4})',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                booking['date'] = match.group(1)
                break
        
        # Ищем время
        time_patterns = [
            r'(\d{1,2}:\d{2})',
            r'(\d{1,2}\.\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                booking['time'] = match.group(1)
                break
        
        # Ищем маршрут
        route_patterns = [
            r'([А-Яа-я\s]+)\s*-\s*([А-Яа-я\s]+)',
            r'из\s+([А-Яа-я\s]+)\s+в\s+([А-Яа-я\s]+)'
        ]
        
        for pattern in route_patterns:
            match = re.search(pattern, text)
            if match:
                booking['from'] = match.group(1).strip()
                booking['to'] = match.group(2).strip()
                break
        
        return booking if booking else None
    
    def get_profile(self) -> Dict[str, Any]:
        """Получить данные профиля (обёртка для get_profile_info)"""
        return self.get_profile_info()
    
    def get_tickets(self) -> List[Dict[str, Any]]:
        """Получить билеты (обёртка для get_bookings)"""
        bookings_data = self.get_bookings()
        return bookings_data.get('bookings', [])
    
    @property
    def is_authenticated(self) -> bool:
        """Проверить аутентификацию"""
        return self.authenticated
    
    @is_authenticated.setter
    def is_authenticated(self, value: bool):
        """Установить статус аутентификации"""
        self.authenticated = value
    
    def close(self):
        """Закрыть сессию"""
        self.session.close()
        logger.info("Сессия закрыта")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Демонстрация работы RequestsAuthManager"""
    # Пример использования
    with RequestsAuthManager() as auth_manager:
        # Попытка входа (с демо-данными)
        logger.info("=== Тестирование входа ===")
        success = auth_manager.login("demo_user", "demo_password")
        
        if success:
            logger.info("Вход выполнен успешно!")
            
            # Получение профиля
            logger.info("=== Получение профиля ===")
            profile = auth_manager.get_profile_info()
            print(f"Профиль: {json.dumps(profile, indent=2, ensure_ascii=False)}")
            
            # Получение бронирований
            logger.info("=== Получение бронирований ===")
            bookings = auth_manager.get_bookings()
            print(f"Бронирования: {json.dumps(bookings, indent=2, ensure_ascii=False)}")
            
        else:
            logger.error("Не удалось выполнить вход")


if __name__ == "__main__":
    main()
