#!/usr/bin/env python3
"""
Модуль автобронирования маршрутов через Requests
"""

import json
import logging
import time
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

# Импортируем существующий менеджер аутентификации
try:
    from ..auth.requests_auth import RequestsAuthManager
except ImportError:
    try:
        from src.auth.requests_auth import RequestsAuthManager
    except ImportError:
        # Заглушка если модуль недоступен
        class RequestsAuthManager:
            def __init__(self):
                self.session = None

logger = logging.getLogger(__name__)

class AutoBookingManager:
    """Менеджер автоматического бронирования маршрутов"""
    
    def __init__(self, auth_manager: RequestsAuthManager):
        self.auth_manager = auth_manager
        self.session = auth_manager.session
    
    def get_available_routes(self, date: str, from_city: str = "Минск", to_city: str = "Островец") -> List[Dict]:
        """
        Получает доступные рейсы для бронирования
        
        Args:
            date: Дата в формате YYYY-MM-DD
            from_city: Город отправления
            to_city: Город назначения
            
        Returns:
            Список доступных рейсов с информацией о местах
        """
        logger.info(f"🔍 Получаем доступные рейсы {from_city} → {to_city} на {date}")
        
        try:
            # Формируем параметры поиска
            search_params = {
                'from': from_city,
                'to': to_city,
                'date': date
            }
            
            # Отправляем запрос поиска
            response = self.session.get(
                'https://билет.маршруточка.бел/search',
                params=search_params
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                routes = self._parse_routes_from_html(soup)
                
                logger.info(f"   Найдено {len(routes)} доступных рейсов")
                return routes
            else:
                logger.error(f"   Ошибка поиска рейсов: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"   Ошибка при получении рейсов: {e}")
            return []
    
    def _parse_routes_from_html(self, soup: BeautifulSoup) -> List[Dict]:
        """Парсит рейсы из HTML"""
        routes = []
        
        # Ищем элементы с рейсами (может потребовать корректировки селекторов)
        route_elements = soup.find_all(['tr', 'div'], class_=['route', 'trip', 'journey'])
        
        for element in route_elements:
            try:
                route_info = self._extract_route_info(element)
                if route_info and route_info.get('available_seats', 0) > 0:
                    routes.append(route_info)
            except Exception as e:
                logger.debug(f"Ошибка парсинга рейса: {e}")
                continue
        
        return routes
    
    def _extract_route_info(self, element) -> Optional[Dict]:
        """Извлекает информацию о рейсе из HTML элемента"""
        try:
            # Ищем время отправления
            departure_time = self._extract_time(element, ['departure', 'depart', 'отправ'])
            
            # Ищем время прибытия
            arrival_time = self._extract_time(element, ['arrival', 'arrive', 'прибыт'])
            
            # Ищем количество доступных мест
            available_seats = self._extract_seats(element)
            
            # Ищем перевозчика
            carrier = self._extract_carrier(element)
            
            # Ищем ID рейса для бронирования
            route_id = self._extract_route_id(element)
            
            if departure_time and available_seats > 0:
                return {
                    'route_id': route_id,
                    'departure_time': departure_time,
                    'arrival_time': arrival_time,
                    'available_seats': available_seats,
                    'carrier': carrier,
                    'booking_url': f"/book/{route_id}" if route_id else None
                }
                
        except Exception as e:
            logger.debug(f"Ошибка извлечения информации: {e}")
            
        return None
    
    def _extract_time(self, element, keywords: List[str]) -> Optional[str]:
        """Извлекает время из элемента"""
        text = element.get_text().lower()
        
        # Ищем время в формате HH:MM
        import re
        time_pattern = r'\b(\d{1,2}:\d{2})\b'
        times = re.findall(time_pattern, text)
        
        if times:
            # Простая эвристика: первое время - отправление, второе - прибытие
            for keyword in keywords:
                if keyword in text:
                    return times[0] if times else None
            return times[0]
        
        return None
    
    def _extract_seats(self, element) -> int:
        """Извлекает количество доступных мест"""
        text = element.get_text().lower()
        
        import re
        # Ищем паттерны типа "5 мест", "мест: 3", "свободно 7"
        seat_patterns = [
            r'(\d+)\s*мест',
            r'мест:?\s*(\d+)',
            r'свободно:?\s*(\d+)',
            r'доступно:?\s*(\d+)',
            r'осталось:?\s*(\d+)'
        ]
        
        for pattern in seat_patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        
        return 0
    
    def _extract_carrier(self, element) -> str:
        """Извлекает название перевозчика"""
        # Ищем в атрибутах или тексте
        carrier_elem = element.find(['span', 'div'], class_=['carrier', 'company', 'перевозчик'])
        if carrier_elem:
            return carrier_elem.get_text().strip()
        
        return "Неизвестно"
    
    def _extract_route_id(self, element) -> Optional[str]:
        """Извлекает ID рейса для бронирования"""
        # Ищем в атрибутах data-*, в ссылках или формах
        route_id = element.get('data-route-id') or element.get('data-id')
        
        if not route_id:
            # Ищем в ссылках
            links = element.find_all('a')
            for link in links:
                href = link.get('href', '')
                if '/book/' in href or '/reserve/' in href:
                    # Извлекаем ID из URL
                    import re
                    match = re.search(r'/(?:book|reserve)/(\w+)', href)
                    if match:
                        route_id = match.group(1)
                        break
        
        return route_id
    
    def auto_book_route(self, route: Dict, passenger_count: int = 1, passenger_info: Optional[Dict] = None) -> Dict:
        """
        Автоматически бронирует рейс
        
        Args:
            route: Информация о рейсе из get_available_routes
            passenger_count: Количество пассажиров (1 или 2)
            passenger_info: Дополнительная информация о пассажире
            
        Returns:
            Результат бронирования
        """
        logger.info(f"🎫 Начинаем автобронирование рейса {route.get('departure_time')}")
        
        try:
            # Проверяем достаточность мест
            available_seats = route.get('available_seats', 0)
            if available_seats < passenger_count:
                return {
                    'success': False,
                    'error': f'Недостаточно мест: доступно {available_seats}, нужно {passenger_count}'
                }
            
            # Переходим на страницу бронирования
            booking_url = route.get('booking_url')
            if not booking_url:
                return {
                    'success': False,
                    'error': 'Не найден URL для бронирования'
                }
            
            # Отправляем запрос на бронирование
            response = self.session.get(f"https://билет.маршруточка.бел{booking_url}")
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Ошибка доступа к странице бронирования: {response.status_code}'
                }
            
            # Парсим форму бронирования
            soup = BeautifulSoup(response.text, 'html.parser')
            booking_form = self._find_booking_form(soup)
            
            if not booking_form:
                return {
                    'success': False,
                    'error': 'Не найдена форма бронирования'
                }
            
            # Заполняем форму бронирования
            form_data = self._prepare_booking_data(booking_form, passenger_count, passenger_info)
            
            # Отправляем бронирование
            booking_result = self._submit_booking(booking_form, form_data)
            
            if booking_result['success']:
                logger.info(f"   ✅ Рейс успешно забронирован: {booking_result.get('booking_id')}")
                return booking_result
            else:
                logger.error(f"   ❌ Ошибка бронирования: {booking_result.get('error')}")
                return booking_result
                
        except Exception as e:
            logger.error(f"   ❌ Критическая ошибка автобронирования: {e}")
            return {
                'success': False,
                'error': f'Критическая ошибка: {str(e)}'
            }
    
    def _find_booking_form(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Находит и анализирует форму бронирования"""
        form = soup.find('form')
        if not form:
            return None
        
        # Анализируем поля формы
        fields = {}
        for input_elem in form.find_all(['input', 'select', 'textarea']):
            name = input_elem.get('name')
            if name:
                fields[name] = {
                    'type': input_elem.get('type', 'text'),
                    'required': input_elem.has_attr('required'),
                    'value': input_elem.get('value', ''),
                    'element': input_elem
                }
        
        return {
            'action': form.get('action', ''),
            'method': form.get('method', 'post'),
            'fields': fields
        }
    
    def _prepare_booking_data(self, form: Dict, passenger_count: int, passenger_info: Optional[Dict]) -> Dict:
        """Подготавливает данные для отправки формы бронирования"""
        form_data = {}
        
        # Заполняем стандартные поля
        for field_name, field_info in form['fields'].items():
            field_type = field_info['type']
            
            if field_name.lower() in ['passenger_count', 'passengers', 'count']:
                form_data[field_name] = str(passenger_count)
            elif field_name.lower() in ['phone', 'telephone']:
                form_data[field_name] = passenger_info.get('phone', '') if passenger_info else ''
            elif field_name.lower() in ['name', 'firstname']:
                form_data[field_name] = passenger_info.get('name', '') if passenger_info else ''
            elif field_type == 'hidden':
                # Сохраняем скрытые поля (CSRF токены и т.д.)
                form_data[field_name] = field_info['value']
            elif field_info['required'] and not form_data.get(field_name):
                # Для обязательных полей ставим значения по умолчанию
                form_data[field_name] = field_info['value'] or 'default'
        
        return form_data
    
    def _submit_booking(self, form: Dict, form_data: Dict) -> Dict:
        """Отправляет форму бронирования"""
        try:
            action_url = form['action']
            if not action_url.startswith('http'):
                action_url = f"https://билет.маршруточка.бел{action_url}"
            
            response = self.session.post(action_url, data=form_data)
            
            if response.status_code == 200:
                # Парсим результат
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ищем признаки успешного бронирования
                success_indicators = [
                    'забронировано', 'успешно', 'подтверждено', 'номер заказа', 'booking confirmed'
                ]
                
                page_text = soup.get_text().lower()
                if any(indicator in page_text for indicator in success_indicators):
                    # Пытаемся извлечь номер бронирования
                    booking_id = self._extract_booking_id(soup)
                    
                    return {
                        'success': True,
                        'booking_id': booking_id,
                        'message': 'Рейс успешно забронирован'
                    }
                else:
                    # Ищем сообщения об ошибках
                    error_message = self._extract_error_message(soup)
                    return {
                        'success': False,
                        'error': error_message or 'Неизвестная ошибка бронирования'
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP ошибка: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка отправки формы: {str(e)}'
            }
    
    def _extract_booking_id(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает ID бронирования из ответа"""
        # Ищем в тексте паттерны типа "Номер заказа: 12345"
        import re
        text = soup.get_text()
        
        patterns = [
            r'номер\s+заказа:?\s*(\w+)',
            r'booking\s+id:?\s*(\w+)',
            r'бронирование:?\s*№?\s*(\w+)',
            r'заказ\s+№\s*(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_error_message(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает сообщение об ошибке"""
        # Ищем элементы с ошибками
        error_selectors = [
            '.error', '.alert-danger', '.message-error',
            '[class*="error"]', '[class*="alert"]'
        ]
        
        for selector in error_selectors:
            error_elem = soup.select_one(selector)
            if error_elem:
                return error_elem.get_text().strip()
        
        return None
    
    def get_user_bookings(self) -> List[Dict]:
        """
        Получает список существующих бронирований пользователя
        
        Returns:
            Список бронирований с деталями
        """
        logger.info("📋 Получаем список бронирований пользователя")
        
        try:
            # Переходим на страницу с бронированиями
            response = self.session.get('https://билет.маршруточка.бел/bookings')
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                bookings = self._parse_bookings_from_html(soup)
                
                logger.info(f"   Найдено {len(bookings)} бронирований")
                return bookings
            else:
                logger.error(f"   Ошибка получения бронирований: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"   Ошибка при получении бронирований: {e}")
            return []
    
    def _parse_bookings_from_html(self, soup: BeautifulSoup) -> List[Dict]:
        """Парсит бронирования из HTML"""
        bookings = []
        
        # Ищем элементы с бронированиями
        booking_elements = soup.find_all(['tr', 'div'], class_=['booking', 'reservation', 'ticket'])
        
        for element in booking_elements:
            try:
                booking_info = self._extract_booking_info(element)
                if booking_info:
                    bookings.append(booking_info)
            except Exception as e:
                logger.debug(f"Ошибка парсинга бронирования: {e}")
                continue
        
        return bookings
    
    def _extract_booking_info(self, element) -> Optional[Dict]:
        """Извлекает информацию о бронировании"""
        try:
            text = element.get_text()
            
            # Извлекаем основную информацию
            booking_id = self._extract_booking_id_from_element(element)
            route_info = self._extract_route_from_element(element)
            date = self._extract_date_from_element(element)
            status = self._extract_status_from_element(element)
            
            if booking_id:
                return {
                    'booking_id': booking_id,
                    'route': route_info,
                    'date': date,
                    'status': status,
                    'raw_text': text.strip()
                }
                
        except Exception as e:
            logger.debug(f"Ошибка извлечения бронирования: {e}")
            
        return None
    
    def _extract_booking_id_from_element(self, element) -> Optional[str]:
        """Извлекает ID бронирования из элемента"""
        # Ищем в атрибутах или тексте
        booking_id = element.get('data-booking-id') or element.get('data-id')
        
        if not booking_id:
            import re
            text = element.get_text()
            patterns = [
                r'№\s*(\w+)',
                r'ID:?\s*(\w+)',
                r'заказ\s*(\w+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    booking_id = match.group(1)
                    break
        
        return booking_id
    
    def _extract_route_from_element(self, element) -> str:
        """Извлекает информацию о маршруте"""
        text = element.get_text()
        
        # Простой поиск направления
        if 'минск' in text.lower() and 'островец' in text.lower():
            if text.lower().find('минск') < text.lower().find('островец'):
                return "Минск → Островец"
            else:
                return "Островец → Минск"
        
        return "Неизвестный маршрут"
    
    def _extract_date_from_element(self, element) -> str:
        """Извлекает дату из элемента"""
        import re
        text = element.get_text()
        
        # Ищем дату в различных форматах
        date_patterns = [
            r'\b(\d{1,2}\.\d{1,2}\.\d{4})\b',
            r'\b(\d{4}-\d{1,2}-\d{1,2})\b',
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return "Неизвестно"
    
    def _extract_status_from_element(self, element) -> str:
        """Извлекает статус бронирования"""
        text = element.get_text().lower()
        
        status_map = {
            'подтвержден': 'confirmed',
            'активен': 'active', 
            'отменен': 'cancelled',
            'истек': 'expired',
            'оплачен': 'paid'
        }
        
        for keyword, status in status_map.items():
            if keyword in text:
                return status
        
        return 'unknown'
