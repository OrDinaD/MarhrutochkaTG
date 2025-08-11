# Улучшенные селекторы для AutoBookingManager на основе анализа Playwright

# В auto_booking.py нужно обновить:

SITE_SELECTORS = {
    'route_container': '.nf-route',
    'route_item': '.nf-route-item',
    'booking_button': '.nf-route-order__action.reservationButton.js_get-bus',
    'time_departure': '.nf-route-item__departure .nf-route-item__time',
    'time_arrival': '.nf-route-item__arrival .nf-route-item__time',
    'price': '.nf-route-order__cost',
    'seats_available': '.nf-route-order__seats',
    'carrier': '.nf-route-item__carrier',
    'duration': '.nf-route-item__duration',
    
    # Форма поиска
    'search_form': '#main-search-form',
    'from_input': 'input[name="from"]',
    'to_input': 'input[name="to"]', 
    'date_input': 'input[name="date"]',
    'passengers_input': 'input[name="passengers"]',
    'search_button': '.search-submit',
    
    # Авторизация
    'login_form': 'form[action*="login"]',
    'phone_input': 'input[name="phone"]',
    'password_input': 'input[name="password"]',
    'login_button': 'button[type="submit"]',
    
    # Бронирование
    'booking_form': '.booking-form',
    'passenger_name': 'input[name="passenger_name"]',
    'passenger_phone': 'input[name="passenger_phone"]',
    'confirm_booking': '.confirm-booking',
}

# Обновленные методы извлечения данных:

def _extract_route_info_updated(self, element) -> Dict:
    """Обновленный метод извлечения информации о рейсе на основе реальной структуры сайта"""
    try:
        # Время отправления
        departure_elem = element.select_one('.nf-route-item__departure .nf-route-item__time')
        departure_time = departure_elem.get_text().strip() if departure_elem else "н/д"
        
        # Время прибытия  
        arrival_elem = element.select_one('.nf-route-item__arrival .nf-route-item__time')
        arrival_time = arrival_elem.get_text().strip() if arrival_elem else "н/д"
        
        # Стоимость
        price_elem = element.select_one('.nf-route-order__cost')
        price_text = price_elem.get_text().strip() if price_elem else "0"
        price = self._extract_price(price_text)
        
        # Количество мест
        seats_elem = element.select_one('.nf-route-order__seats')
        seats_text = seats_elem.get_text().strip() if seats_elem else "0"
        available_seats = self._extract_seats_count(seats_text)
        
        # Перевозчик
        carrier_elem = element.select_one('.nf-route-item__carrier')
        carrier = carrier_elem.get_text().strip() if carrier_elem else "Неизвестно"
        
        # Длительность
        duration_elem = element.select_one('.nf-route-item__duration')
        duration = duration_elem.get_text().strip() if duration_elem else "н/д"
        
        # URL для бронирования (из кнопки)
        booking_btn = element.select_one('.nf-route-order__action.reservationButton')
        booking_url = booking_btn.get('href') if booking_btn else None
        
        # ID рейса (может быть в data-атрибутах)
        route_id = element.get('data-route-id') or element.get('data-id')
        if not route_id and booking_btn:
            # Попробуем извлечь из onclick или data-атрибутов кнопки
            onclick = booking_btn.get('onclick', '')
            if 'reserveRoute' in onclick:
                import re
                match = re.search(r'reserveRoute\(([^)]+)\)', onclick)
                if match:
                    route_id = match.group(1).strip('\'"')
        
        return {
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'price': price,
            'available_seats': available_seats,
            'carrier': carrier,
            'duration': duration,
            'booking_url': booking_url,
            'route_id': route_id,
            'raw_element': str(element)  # Для отладки
        }
        
    except Exception as e:
        logger.error(f"Ошибка извлечения данных рейса: {e}")
        return {
            'departure_time': "н/д",
            'arrival_time': "н/д", 
            'price': 0,
            'available_seats': 0,
            'carrier': "Ошибка",
            'duration': "н/д",
            'booking_url': None,
            'route_id': None
        }

def _extract_price_updated(self, price_text: str) -> float:
    """Улучшенное извлечение цены с учетом формата сайта"""
    if not price_text:
        return 0.0
    
    # Удаляем все кроме цифр, точек и запятых
    import re
    price_clean = re.sub(r'[^\d.,]', '', price_text.replace(',', '.'))
    
    try:
        return float(price_clean)
    except (ValueError, TypeError):
        return 0.0

def _extract_seats_count_updated(self, seats_text: str) -> int:
    """Улучшенное извлечение количества мест"""
    if not seats_text:
        return 0
    
    # Паттерны для беларусского сайта
    patterns = [
        r'(\d+)\s*мест',
        r'(\d+)\s*свободных?',
        r'(\d+)\s*доступно',
        r'свободно\s*(\d+)',
        r'осталось\s*(\d+)',
        r'^(\d+)$'  # Просто число
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, seats_text.lower())
        if match:
            return int(match.group(1))
    
    return 0

# Метод для работы с новой структурой кнопок бронирования:

async def _click_booking_button_updated(self, route_element):
    """Обновленный метод клика по кнопке бронирования"""
    try:
        # Ищем кнопку бронирования в элементе рейса
        booking_btn = route_element.select_one('.nf-route-order__action.reservationButton.js_get-bus')
        
        if not booking_btn:
            logger.error("Кнопка бронирования не найдена")
            return False
        
        # Проверяем доступность кнопки
        if 'disabled' in booking_btn.get('class', []):
            logger.warning("Кнопка бронирования недоступна")
            return False
        
        # Получаем URL или параметры для бронирования
        href = booking_btn.get('href')
        onclick = booking_btn.get('onclick', '')
        
        if href:
            # Переходим по ссылке
            response = self.session.get(f"https://билет.маршруточка.бел{href}")
            return response.status_code == 200
        elif onclick:
            # Выполняем JavaScript функцию (имитируем)
            if 'reserveRoute' in onclick:
                # Извлекаем параметры и отправляем AJAX запрос
                return await self._handle_reserve_route_js(onclick)
        
        return False
        
    except Exception as e:
        logger.error(f"Ошибка клика по кнопке бронирования: {e}")
        return False

async def _handle_reserve_route_js(self, onclick_code: str):
    """Обработка JavaScript функции reserveRoute"""
    try:
        import re
        # Извлекаем параметры из onclick
        match = re.search(r'reserveRoute\(([^)]+)\)', onclick_code)
        if not match:
            return False
        
        params_str = match.group(1)
        # Простой парсинг параметров (может потребоваться улучшение)
        params = [p.strip('\'" ') for p in params_str.split(',')]
        
        # Формируем данные для AJAX запроса
        ajax_data = {
            'action': 'reserve_route',
            'route_id': params[0] if params else '',
            'passenger_count': 1,
        }
        
        # Отправляем AJAX запрос
        response = self.session.post(
            "https://билет.маршруточка.бел/ajax/reserve",
            json=ajax_data,
            headers={
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        )
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Ошибка обработки JavaScript бронирования: {e}")
        return False
