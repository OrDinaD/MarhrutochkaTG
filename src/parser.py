import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class FinalMarshrutochkaParser:
    """Финальный парсер для сайта билет.маршруточка.бел"""

    def __init__(self, enable_cache: bool = False):
        self.base_url = "https://билет.маршруточка.бел"
        self.session = None
        self.enable_cache = enable_cache
        self._cache: Dict[tuple, str] = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def clear_cache(self) -> None:
        """Очистить кэш расписаний."""
        self._cache.clear()

    def _cache_key(self, from_city_id: str, to_city_id: str, date: str) -> tuple:
        """Create a cache key for schedule requests."""
        return from_city_id, to_city_id, date
    
    async def get_schedule_html(self, from_city_id: str, to_city_id: str, date: str) -> Optional[str]:
        """Получить HTML с расписанием"""
        try:
            url = f"{self.base_url}/schedules"
            params = {
                'city_from_id': from_city_id,
                'city_to_id': to_city_id,
                'date': date
            }
            
            cache_key = self._cache_key(from_city_id, to_city_id, date)

            if self.enable_cache and cache_key in self._cache:
                logger.info(f"Используем кэш для {cache_key}")
                return self._cache[cache_key]

            logger.info(f"Запрашиваем расписание: {url} с параметрами {params}")

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if isinstance(data, dict) and 'html' in data:
                        html = data['html']
                        if self.enable_cache:
                            self._cache[cache_key] = html
                        return html

                    return None
                else:
                    logger.error(f"HTTP ошибка: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при запросе HTML расписания: {e}")
            return None
    
    def parse_html_schedule(self, html_content: str, from_city: str, to_city: str, date: str) -> List[Dict]:
        """Парсинг HTML расписания"""
        routes = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем все блоки маршрутов
            route_blocks = soup.find_all('div', class_='nf-route')
            logger.info(f"Найдено блоков маршрутов: {len(route_blocks)}")
            
            for i, route_block in enumerate(route_blocks):
                try:
                    route_info = self.extract_route_from_block(route_block, from_city, to_city, date)
                    if route_info:
                        routes.append(route_info)
                        logger.info(
                            f"Маршрут {i+1}: {route_info['departure_time']} -> {route_info['arrival_time']}, "
                            f"свободно мест: {route_info.get('available_seats')}, "
                            f"перевозчик: {route_info.get('carrier')}"
                        )
                except Exception as e:
                    logger.error(f"Ошибка при обработке маршрута {i+1}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге HTML: {e}")
            import traceback
            traceback.print_exc()
        
        return routes
    
    def extract_route_from_block(self, route_block, from_city: str, to_city: str, date: str) -> Optional[Dict]:
        """Извлечение информации о маршруте из HTML блока"""
        try:
            route_info = {
                'from_city': from_city,
                'to_city': to_city,
                'date': date,
                'parsed_at': datetime.now().isoformat()
            }
            
            # Извлекаем времена отправления и прибытия
            time_elements = route_block.find_all('div', class_='nf-route-point__time')
            if len(time_elements) >= 2:
                route_info['departure_time'] = time_elements[0].get_text().strip()
                route_info['arrival_time'] = time_elements[1].get_text().strip()
            
            # Извлекаем длительность поездки
            duration_element = route_block.find('div', class_='nf-route-transport__duration')
            if duration_element:
                route_info['duration'] = duration_element.get_text().strip()
            
            # Извлекаем количество свободных мест
            seats_text = route_block.find('div', class_='nf-route-transport-seats')
            if seats_text:
                seats_full_text = seats_text.get_text()
                # Ищем число после "свободно:"
                seats_match = re.search(r'свободно:\s*(\d+)', seats_full_text)
                if seats_match:
                    route_info['available_seats'] = int(seats_match.group(1))
            
            # Извлекаем перевозчика
            carrier_element = route_block.find('div', class_='nf-route__company')
            if carrier_element:
                route_info['carrier'] = carrier_element.get_text().strip()
            else:
                # Альтернативный способ поиска перевозчика
                search_element = route_block.find('div', class_='nf-route__search')
                if search_element:
                    route_info['carrier'] = search_element.get_text().strip()
            
            # Извлекаем цену
            cost_element = route_block.find('div', class_='nf-route-order__cost')
            if cost_element:
                cost_text = cost_element.get_text()
                # Ищем число перед "BYN" или "руб"
                price_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:BYN|руб)', cost_text)
                if price_match:
                    price_str = price_match.group(1).replace(',', '.')
                    route_info['price'] = float(price_str) if price_str != '0' else None
                    route_info['price_str'] = cost_text.strip()
            
            # Извлекаем тип оплаты
            payment_element = route_block.find('div', class_='nf-route__payment')
            if payment_element:
                route_info['payment_method'] = payment_element.get_text().strip()
            
            # Извлекаем URL для бронирования
            reservation_button = route_block.find('button', class_='reservationButton')
            if reservation_button:
                reservation_url = reservation_button.get('data-url')
                if reservation_url:
                    route_info['reservation_url'] = reservation_url
            
            # Проверяем, что у нас есть минимальные данные
            if route_info.get('departure_time') and route_info.get('arrival_time'):
                return route_info
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении данных маршрута: {e}")
        
        return None
    
    async def search_routes(self, from_city: str, to_city: str, date: str) -> List[Dict]:
        """Поиск маршрутов между городами на указанную дату"""
        
        city_mapping = {
            "Минск": "5",
            "Островец": "23"
        }
        
        from_city_id = city_mapping.get(from_city)
        to_city_id = city_mapping.get(to_city)
        
        if not from_city_id or not to_city_id:
            logger.warning(f"Неизвестные города: {from_city} или {to_city}")
            return []
        
        # Получаем HTML
        html_content = await self.get_schedule_html(from_city_id, to_city_id, date)
        
        if html_content:
            # Парсим HTML
            return self.parse_html_schedule(html_content, from_city, to_city, date)
        
        return []
    
    async def get_routes_minsk_ostrovets(self, date: str) -> List[Dict]:
        """Получить маршруты Минск-Островец"""
        return await self.search_routes("Минск", "Островец", date)
    
    async def get_routes_ostrovets_minsk(self, date: str) -> List[Dict]:
        """Получить маршруты Островец-Минск"""
        return await self.search_routes("Островец", "Минск", date)
    
    async def get_all_routes(self, date: str) -> Dict[str, List[Dict]]:
        """Получить все маршруты в обе стороны"""
        result = {
            'minsk_to_ostrovets': [],
            'ostrovets_to_minsk': [],
            'search_date': date,
            'search_time': datetime.now().isoformat(),
            'success': False
        }
        
        try:
            # Получаем маршруты в обе стороны
            logger.info("Поиск маршрутов Минск-Островец...")
            result['minsk_to_ostrovets'] = await self.get_routes_minsk_ostrovets(date)

            logger.info("Поиск маршрутов Островец-Минск...")
            result['ostrovets_to_minsk'] = await self.get_routes_ostrovets_minsk(date)
            
            # Успех только если получили хотя бы один рейс
            if result['minsk_to_ostrovets'] or result['ostrovets_to_minsk']:
                result['success'] = True
            
        except Exception as e:
            logger.error(f"Ошибка при получении всех маршрутов: {e}")
            result['error'] = str(e)
        
        return result


async def main():
    """Основная функция для тестирования финального парсера"""
    # Получаем завтрашнюю дату
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    async with FinalMarshrutochkaParser() as parser:
        # Получаем все маршруты на завтра
        routes = await parser.get_all_routes(tomorrow)
        
        # Выводим результаты
        logger.info("\n" + "="*70)
        logger.info("РЕЗУЛЬТАТЫ ПАРСИНГА МАРШРУТОВ")
        logger.info("="*70)
        logger.info(f"Дата поиска: {tomorrow}")
        logger.info(f"Время поиска: {routes['search_time']}")
        logger.info(f"Статус: {'Успешно' if routes['success'] else 'Ошибка'}")
        
        logger.info(f"\nМаршруты Минск-Островец: {len(routes['minsk_to_ostrovets'])}")
        for i, route in enumerate(routes['minsk_to_ostrovets'], 1):
            logger.info(f"  {i}. {route['departure_time']} → {route['arrival_time']}")
            logger.info(f"     Длительность: {route.get('duration', 'н/д')}")
            logger.info(f"     Свободных мест: {route.get('available_seats', 'н/д')}")
            logger.info(f"     Перевозчик: {route.get('carrier', 'н/д')}")
            logger.info(f"     Цена: {route.get('price_str', 'н/д')}")
            logger.info("")
        
        logger.info(f"\nМаршруты Островец-Минск: {len(routes['ostrovets_to_minsk'])}")
        for i, route in enumerate(routes['ostrovets_to_minsk'], 1):
            logger.info(f"  {i}. {route['departure_time']} → {route['arrival_time']}")
            logger.info(f"     Длительность: {route.get('duration', 'н/д')}")
            logger.info(f"     Свободных мест: {route.get('available_seats', 'н/д')}")
            logger.info(f"     Перевозчик: {route.get('carrier', 'н/д')}")
            logger.info(f"     Цена: {route.get('price_str', 'н/д')}")
            logger.info("")
        
        # Сохраняем результаты в файл
        filename = f'final_routes_{tomorrow}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(routes, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Результаты сохранены в файл {filename}")
        
        # Краткая статистика
        total_routes = len(routes['minsk_to_ostrovets']) + len(routes['ostrovets_to_minsk'])
        logger.info(f"\nВсего найдено маршрутов: {total_routes}")


if __name__ == "__main__":
    asyncio.run(main())
