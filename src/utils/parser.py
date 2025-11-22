import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from bs4 import BeautifulSoup
import re
from monitoring.railway_logger_enhanced import railway_logger

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
                railway_logger.info(f"Используем кэш для {cache_key}", extra={"cache_key": str(cache_key)})
                return self._cache[cache_key]

            railway_logger.monitoring_action(f"Запрашиваем расписание: {url}", data={"params": params})

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
                    railway_logger.error(f"HTTP ошибка: {response.status}", extra={"status_code": response.status, "url": url})
                    return None
        except Exception as e:
            railway_logger.error(f"Ошибка при запросе HTML расписания: {e}", exc_info=True, extra={"url": url if 'url' in locals() else None})
            return None
    
    def parse_html_schedule(self, html_content: str, from_city: str, to_city: str, date: str) -> List[Dict]:
        """Парсинг HTML расписания"""
        routes = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем все блоки маршрутов
            route_blocks = soup.find_all('div', class_='nf-route')
            railway_logger.info(f"Найдено блоков маршрутов: {len(route_blocks)}", extra={"count": len(route_blocks)})
            
            for i, route_block in enumerate(route_blocks):
                try:
                    route_info = self.extract_route_from_block(route_block, from_city, to_city, date)
                    if route_info:
                        routes.append(route_info)
                        railway_logger.info(
                            f"Маршрут {i+1}: {route_info['departure_time']} -> {route_info['arrival_time']}",
                            extra={
                                "available_seats": route_info.get('available_seats'),
                                "carrier": route_info.get('carrier')
                            }
                        )
                except Exception as e:
                    railway_logger.error(f"Ошибка при обработке маршрута {i+1}: {e}", exc_info=True)
                    continue
            
        except Exception as e:
            railway_logger.error(f"Ошибка при парсинге HTML: {e}", exc_info=True)
        
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
            
            # НОВОЕ: Анализ промежуточных городов и типа маршрута
            route_text = route_block.get_text()
            
            # Инициализируем поля для анализа
            route_info['via_smorgon'] = False
            route_info['via_oshmiany'] = False
            route_info['intermediate_cities'] = []
            route_info['route_type'] = 'unknown'
            
            # Проверяем упоминание конкретных городов в тексте
            if "Сморгонь" in route_text or "сморгонь" in route_text.lower():
                route_info['via_smorgon'] = True
                route_info['intermediate_cities'] = ["Сморгонь"]
                route_info['route_type'] = 'via_smorgon'
            elif "Ошмяны" in route_text or "ошмяны" in route_text.lower():
                route_info['via_oshmiany'] = True
                route_info['intermediate_cities'] = ["Ошмяны"]
                route_info['route_type'] = 'via_oshmiany'
            
            # Анализ по времени в пути (если прямого указания нет)
            if route_info.get('duration') and route_info['route_type'] == 'unknown':
                duration_str = route_info['duration']
                # Парсим длительность (например: "2 ч 25 мин")
                hours_match = re.search(r'(\d+)\s*ч', duration_str)
                minutes_match = re.search(r'(\d+)\s*мин', duration_str)
                
                total_minutes = 0
                if hours_match:
                    total_minutes += int(hours_match.group(1)) * 60
                if minutes_match:
                    total_minutes += int(minutes_match.group(1))
                
                route_info['duration_minutes'] = total_minutes
                
                # Определяем тип маршрута по времени
                if 180 <= total_minutes <= 210:  # ~3ч 10мин - через Сморгонь
                    route_info['via_smorgon'] = True
                    route_info['intermediate_cities'] = ["Сморгонь"]
                    route_info['route_type'] = 'via_smorgon_estimated'
                elif 120 <= total_minutes <= 135:  # ~2ч 10мин - через Ошмяны
                    route_info['via_oshmiany'] = True
                    route_info['intermediate_cities'] = ["Ошмяны"]
                    route_info['route_type'] = 'via_oshmiany_estimated'
                else:
                    route_info['route_type'] = 'direct_or_unknown'
            
            # Извлекаем описание маршрута (если есть)
            route_description_elements = route_block.find_all('div', class_=['nf-route-point__location', 'nf-route__description'])
            if route_description_elements:
                descriptions = [elem.get_text().strip() for elem in route_description_elements]
                route_info['route_description'] = ' '.join(descriptions)
            
            # Проверяем, что у нас есть минимальные данные
            if route_info.get('departure_time') and route_info.get('arrival_time'):
                return route_info
            
        except Exception as e:
            railway_logger.error(f"Ошибка при извлечении данных маршрута: {e}", exc_info=True)
        
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
            railway_logger.warning(f"Неизвестные города: {from_city} или {to_city}")
            return []
        
        # Получаем HTML
        html_content = await self.get_schedule_html(from_city_id, to_city_id, date)
        
        if html_content:
            # Парсим HTML
            return self.parse_html_schedule(html_content, from_city, to_city, date)
        
        return []
    
    async def get_routes_minsk_ostrovets(self, date: str) -> List[Dict]:
        """Получить маршруты Минск-Островец (статическое расписание через Сморгонь)"""
        from .route_analyzer import generate_static_minsk_smorgon_ostrovets_schedule
        
        # Используем статическое расписание для маршрута через Сморгонь
        try:
            # Сначала получаем реальные данные для улучшения расчетов времени
            real_routes = await self.search_routes("Минск", "Островец", date)
            
            # Передаем реальные данные в генератор статического расписания
            static_routes = generate_static_minsk_smorgon_ostrovets_schedule(date, real_routes)
            railway_logger.info(f"Сгенерировано {len(static_routes)} статических маршрутов Минск-Островец через Сморгонь с учетом реальных данных")
            return static_routes
        except Exception as e:
            railway_logger.error(f"Ошибка генерации статического расписания: {e}", exc_info=True)
            # Fallback на обычный парсинг
            return await self.search_routes("Минск", "Островец", date)
    
    async def get_routes_ostrovets_minsk(self, date: str) -> List[Dict]:
        """Получить маршруты Островец-Минск"""
        return await self.search_routes("Островец", "Минск", date)
    
    async def get_routes_minsk_smorgon(self, date: str) -> List[Dict]:
        """Получить маршруты Минск-Сморгонь (включая транзитные)"""
        # Получаем все маршруты Минск-Островец и фильтруем те, что проходят через Сморгонь
        all_routes = await self.search_routes("Минск", "Островец", date)
        smorgon_routes = []
        
        for route in all_routes:
            if route.get('via_smorgon') or "Сморгонь" in route.get('route_description', ''):
                # Создаем копию маршрута для Минск-Сморгонь
                smorgon_route = route.copy()
                smorgon_route['to_city'] = 'Сморгонь'
                
                # Пытаемся вычислить время прибытия в Сморгонь
                departure_time = route.get('departure_time')
                if departure_time:
                    try:
                        from .route_analyzer import RouteAnalyzer
                        smorgon_arrival = RouteAnalyzer.calculate_intermediate_arrival_time(
                            departure_time, "Островец", 
                            ["Минск", "Сморгонь", "Островец"], "Сморгонь"
                        )
                        if smorgon_arrival:
                            smorgon_route['arrival_time'] = smorgon_arrival
                            # Обновляем длительность
                            smorgon_route['duration'] = "~2 ч 5 мин"
                    except:
                        pass
                
                smorgon_routes.append(smorgon_route)
        
        return smorgon_routes
    
    async def get_routes_smorgon_minsk(self, date: str) -> List[Dict]:
        """Получить маршруты Сморгонь-Минск (включая транзитные)"""
        # Получаем все маршруты Островец-Минск и фильтруем те, что проходят через Сморгонь
        all_routes = await self.search_routes("Островец", "Минск", date)
        smorgon_routes = []
        
        for route in all_routes:
            if route.get('via_smorgon') or "Сморгонь" in route.get('route_description', ''):
                # Создаем копию маршрута для Сморгонь-Минск
                smorgon_route = route.copy()
                smorgon_route['from_city'] = 'Сморгонь'
                
                # Пытаемся вычислить время отправления из Сморгони
                arrival_time = route.get('arrival_time')
                if arrival_time:
                    try:
                        from .route_analyzer import RouteAnalyzer
                        # Вычисляем время отправления из Сморгони (прибытие в Минск минус ~2ч 5мин)
                        from datetime import datetime, timedelta
                        arrival_dt = datetime.strptime(arrival_time, "%H:%M")
                        departure_dt = arrival_dt - timedelta(minutes=125)  # ~2ч 5мин от Сморгони до Минска
                        smorgon_route['departure_time'] = departure_dt.strftime("%H:%M")
                        # Обновляем длительность
                        smorgon_route['duration'] = "~2 ч 5 мин"
                    except:
                        pass
                
                smorgon_routes.append(smorgon_route)
        
        return smorgon_routes
    
    async def get_routes_ostrovets_smorgon(self, date: str) -> List[Dict]:
        """Получить маршруты Островец-Сморгонь (включая транзитные)"""
        # Получаем все маршруты Островец-Минск и фильтруем те, что проходят через Сморгонь
        all_routes = await self.search_routes("Островец", "Минск", date)
        smorgon_routes = []
        
        for route in all_routes:
            if route.get('via_smorgon') or "Сморгонь" in route.get('route_description', ''):
                # Создаем копию маршрута для Островец-Сморгонь
                smorgon_route = route.copy()
                smorgon_route['to_city'] = 'Сморгонь'
                
                # Пытаемся вычислить время прибытия в Сморгонь
                departure_time = route.get('departure_time')
                if departure_time:
                    try:
                        from .route_analyzer import RouteAnalyzer
                        smorgon_arrival = RouteAnalyzer.calculate_intermediate_arrival_time(
                            departure_time, "Минск", 
                            ["Островец", "Сморгонь", "Минск"], "Сморгонь"
                        )
                        if smorgon_arrival:
                            smorgon_route['arrival_time'] = smorgon_arrival
                            # Обновляем длительность
                            smorgon_route['duration'] = "~1 ч 5 мин"
                    except:
                        pass
                
                smorgon_routes.append(smorgon_route)
        
        return smorgon_routes
    
    async def get_routes_smorgon_ostrovets(self, date: str) -> List[Dict]:
        """Получить маршруты Сморгонь-Островец (включая транзитные)"""
        # Получаем все маршруты Минск-Островец и фильтруем те, что проходят через Сморгонь
        all_routes = await self.search_routes("Минск", "Островец", date)
        smorgon_routes = []
        
        # Получаем среднее время от Сморгони до Островца и от Минска до Сморгони на основе реальных данных
        from .route_analyzer import RouteAnalyzer
        avg_smorgon_ostrovets_duration = RouteAnalyzer.get_average_smorgon_ostrovets_duration(all_routes)
        avg_minsk_smorgon_duration = RouteAnalyzer.get_average_minsk_smorgon_duration(all_routes)
        
        for route in all_routes:
            if route.get('via_smorgon') or "Сморгонь" in route.get('route_description', ''):
                # Создаем копию маршрута для Сморгонь-Островец
                smorgon_route = route.copy()
                smorgon_route['from_city'] = 'Сморгонь'
                
                # Пытаемся вычислить время отправления из Сморгони
                arrival_time = route.get('arrival_time')
                departure_time = route.get('departure_time')
                if departure_time and arrival_time:
                    try:
                        # Вычисляем динамическое время от Сморгони до Островца для этого конкретного маршрута
                        dynamic_smorgon_ostrovets_duration = RouteAnalyzer.calculate_smorgon_ostrovets_duration(route)
                        dynamic_minsk_smorgon_duration = RouteAnalyzer.calculate_minsk_smorgon_duration(route)
                        
                        # Используем динамические данные если доступны, иначе средние
                        if dynamic_smorgon_ostrovets_duration:
                            duration_minutes = dynamic_smorgon_ostrovets_duration
                        else:
                            duration_minutes = avg_smorgon_ostrovets_duration
                            
                        if dynamic_minsk_smorgon_duration:
                            minsk_smorgon_time = dynamic_minsk_smorgon_duration
                        else:
                            minsk_smorgon_time = avg_minsk_smorgon_duration
                        
                        # Вычисляем время отправления из Сморгони (отправление из Минска + время до Сморгони)
                        from datetime import datetime, timedelta
                        departure_dt = datetime.strptime(departure_time, "%H:%M")
                        smorgon_departure_dt = departure_dt + timedelta(minutes=minsk_smorgon_time)
                        smorgon_route['departure_time'] = smorgon_departure_dt.strftime("%H:%M")
                        
                        # Обновляем длительность на основе реальных данных
                        hours = duration_minutes // 60
                        minutes = duration_minutes % 60
                        if hours > 0:
                            smorgon_route['duration'] = f"~{hours} ч {minutes} мин"
                        else:
                            smorgon_route['duration'] = f"~{minutes} мин"
                            
                        # Сохраняем рассчитанные времена для отладки
                        smorgon_route['calculated_duration_minutes'] = duration_minutes
                        smorgon_route['calculated_minsk_smorgon_minutes'] = minsk_smorgon_time
                        
                    except Exception as e:
                        railway_logger.error(f"Ошибка при расчете времени для маршрута Сморгонь-Островец: {e}", exc_info=True)
                        # Fallback к стандартному времени
                        smorgon_route['duration'] = "~1 ч 5 мин"
                
                smorgon_routes.append(smorgon_route)
        
        railway_logger.info(f"Создано {len(smorgon_routes)} маршрутов Сморгонь-Островец с динамически рассчитанным временем")
        return smorgon_routes
    
    async def get_all_routes(self, date: str) -> Dict[str, List[Dict]]:
        """Получить все маршруты в обе стороны, включая через Сморгонь"""
        result = {
            'minsk_to_ostrovets': [],
            'ostrovets_to_minsk': [],
            'minsk_to_smorgon': [],
            'smorgon_to_minsk': [],
            'ostrovets_to_smorgon': [],
            'smorgon_to_ostrovets': [],
            'search_date': date,
            'search_time': datetime.now().isoformat(),
            'success': False
        }
        
        try:
            # Получаем основные маршруты
            railway_logger.info("Поиск маршрутов Минск-Островец...")
            result['minsk_to_ostrovets'] = await self.get_routes_minsk_ostrovets(date)

            railway_logger.info("Поиск маршрутов Островец-Минск...")
            result['ostrovets_to_minsk'] = await self.get_routes_ostrovets_minsk(date)
            
            # Получаем маршруты через Сморгонь
            railway_logger.info("Поиск маршрутов Минск-Сморгонь...")
            result['minsk_to_smorgon'] = await self.get_routes_minsk_smorgon(date)
            
            railway_logger.info("Поиск маршрутов Сморгонь-Минск...")
            result['smorgon_to_minsk'] = await self.get_routes_smorgon_minsk(date)
            
            railway_logger.info("Поиск маршрутов Островец-Сморгонь...")
            result['ostrovets_to_smorgon'] = await self.get_routes_ostrovets_smorgon(date)
            
            railway_logger.info("Поиск маршрутов Сморгонь-Островец...")
            result['smorgon_to_ostrovets'] = await self.get_routes_smorgon_ostrovets(date)
            
            # Подсчитываем общее количество найденных маршрутов
            total_routes = sum(len(routes) for routes in result.values() if isinstance(routes, list))
            
            # Успех если получили хотя бы один рейс
            if total_routes > 0:
                result['success'] = True
                result['total_routes'] = total_routes
            
        except Exception as e:
            railway_logger.error(f"Ошибка при получении всех маршрутов: {e}", exc_info=True)
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
        railway_logger.info("\n" + "="*70)
        railway_logger.info("РЕЗУЛЬТАТЫ ПАРСИНГА МАРШРУТОВ")
        railway_logger.info("="*70)
        railway_logger.info(f"Дата поиска: {tomorrow}")
        railway_logger.info(f"Время поиска: {routes['search_time']}")
        railway_logger.info(f"Статус: {'Успешно' if routes['success'] else 'Ошибка'}")
        
        railway_logger.info(f"\nМаршруты Минск-Островец: {len(routes['minsk_to_ostrovets'])}")
        for i, route in enumerate(routes['minsk_to_ostrovets'], 1):
            railway_logger.info(f"  {i}. {route['departure_time']} → {route['arrival_time']}")
            railway_logger.info(f"     Длительность: {route.get('duration', 'н/д')}")
            railway_logger.info(f"     Свободных мест: {route.get('available_seats', 'н/д')}")
            railway_logger.info(f"     Перевозчик: {route.get('carrier', 'н/д')}")
            railway_logger.info(f"     Цена: {route.get('price_str', 'н/д')}")
            railway_logger.info("")
        
        railway_logger.info(f"\nМаршруты Островец-Минск: {len(routes['ostrovets_to_minsk'])}")
        for i, route in enumerate(routes['ostrovets_to_minsk'], 1):
            railway_logger.info(f"  {i}. {route['departure_time']} → {route['arrival_time']}")
            railway_logger.info(f"     Длительность: {route.get('duration', 'н/д')}")
            railway_logger.info(f"     Свободных мест: {route.get('available_seats', 'н/д')}")
            railway_logger.info(f"     Перевозчик: {route.get('carrier', 'н/д')}")
            railway_logger.info(f"     Цена: {route.get('price_str', 'н/д')}")
            railway_logger.info("")
        
        # Сохраняем результаты в файл
        filename = f'final_routes_{tomorrow}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(routes, f, ensure_ascii=False, indent=2)
        
        railway_logger.info(f"Результаты сохранены в файл {filename}")
        
        # Краткая статистика
        total_routes = len(routes['minsk_to_ostrovets']) + len(routes['ostrovets_to_minsk'])
        railway_logger.info(f"\nВсего найдено маршрутов: {total_routes}")


if __name__ == "__main__":
    asyncio.run(main())
