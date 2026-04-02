#!/usr/bin/env python3
"""
Парсер для нового API BusPro.by (Маршруточка Плюс)
Работает напрямую с API https://buspro.by/api
"""

import asyncio
import logging
import aiohttp
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# Добавляем src в путь для импортов
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
SRC_PATH = os.path.dirname(PROJECT_ROOT)
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

try:
    from monitoring.railway_logger_enhanced import railway_logger
except ImportError:
    # Fallback для прямого запуска
    railway_logger = None

logger = logging.getLogger(__name__)


def _safe_log_info(message: str, extra: Dict = None):
    """Безопасное логирование с railway_logger или стандартным logger"""
    if railway_logger:
        if extra:
            railway_logger.info(message, extra=extra)
        else:
            railway_logger.info(message)
    else:
        if extra:
            logger.info(f"{message} | {extra}")
        else:
            logger.info(message)


def _safe_log_error(message: str, extra: Dict = None, exc_info: bool = False):
    """Безопасное логирование ошибок"""
    if railway_logger:
        if extra:
            railway_logger.error(message, extra=extra, exc_info=exc_info)
        else:
            railway_logger.error(message, exc_info=exc_info)
    else:
        if extra:
            logger.error(f"{message} | {extra}")
        else:
            logger.error(message)
        if exc_info:
            logger.exception("Exception details:")


def _safe_log_warning(message: str, extra: Dict = None):
    """Безопасное логирование предупреждений"""
    if railway_logger:
        if extra:
            railway_logger.warning(message, extra=extra)
        else:
            railway_logger.warning(message)
    else:
        if extra:
            logger.warning(f"{message} | {extra}")
        else:
            logger.warning(message)


def _safe_log_monitoring_action(message: str, data: Dict = None):
    """Безопасное логирование действий мониторинга"""
    if railway_logger and hasattr(railway_logger, 'monitoring_action'):
        railway_logger.monitoring_action(message, data=data or {})
    else:
        if data:
            logger.info(f"MONITOR: {message} | {data}")
        else:
            logger.info(f"MONITOR: {message}")


class BusproAPIParser:
    """Парсер для API BusPro.by"""

    API_BASE = "https://buspro.by/api"
    COMPANY_ID = "35"

    # Карта городов
    CITIES = {
        "519": "Минск",
        "520": "Островец",
        "521": "Сморгонь",
        "522": "Ошмяны",
    }

    # Обратная карта
    CITY_IDS = {
        "Минск": "519",
        "Островец": "520",
        "Сморгонь": "521",
        "Ошмяны": "522",
    }

    def __init__(self, enable_cache: bool = True):
        self.session: Optional[aiohttp.ClientSession] = None
        self.enable_cache = enable_cache
        self._cache: Dict[str, Tuple[any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)  # Кэш на 5 минут

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        if railway_logger:
            railway_logger.info("BusproAPIParser: сессия создана")
        else:
            logger.info("BusproAPIParser: сессия создана")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.session:
            await self.session.close()
            if railway_logger:
                railway_logger.info("BusproAPIParser: сессия закрыта")
            else:
                logger.info("BusproAPIParser: сессия закрыта")

    def _cache_key(self, endpoint: str, params: Dict) -> str:
        """Создание ключа кэша"""
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint}?{param_str}"

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Проверка валидности кэша"""
        return datetime.now() - timestamp < self._cache_ttl

    async def _request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Optional[Dict]:
        """Базовый запрос к API"""
        if not self.session:
            _safe_log_error("BusproAPIParser: сессия не инициализирована")
            return None

        url = f"{self.API_BASE}{endpoint}"
        cache_key = self._cache_key(endpoint, params or {})

        # Проверка кэша для GET запросов
        if method == "GET" and self.enable_cache and cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if self._is_cache_valid(timestamp):
                _safe_log_info(f"BusproAPIParser: кэш hit для {endpoint}", extra={"cache_key": cache_key})
                return data
            else:
                _safe_log_info(f"BusproAPIParser: кэш просрочен для {endpoint}")
                del self._cache[cache_key]

        try:
            _safe_log_monitoring_action(f"BusproAPIParser: запрос к {endpoint}", data={"params": params})

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # Сохраняем в кэш
                    if method == "GET" and self.enable_cache:
                        self._cache[cache_key] = (data, datetime.now())
                        _safe_log_info(f"BusproAPIParser: кэш saved для {endpoint}")

                    return data
                else:
                    _safe_log_error(
                        f"BusproAPIParser: HTTP ошибка {response.status}",
                        extra={"url": url, "status": response.status}
                    )
                    return None

        except aiohttp.ClientError as e:
            _safe_log_error(f"BusproAPIParser: ошибка соединения: {e}", exc_info=True)
            return None
        except Exception as e:
            _safe_log_error(f"BusproAPIParser: неожиданная ошибка: {e}", exc_info=True)
            return None

    async def get_routes(self, city_departure_id: str = None) -> List[Dict]:
        """
        Получение списка маршрутов компании

        :param city_departure_id: Опционально, ID города отправления для фильтрации
        :return: Список маршрутов
        """
        params = {"s[company_id]": self.COMPANY_ID}

        if city_departure_id:
            params["s[city_departure_id]"] = city_departure_id

        data = await self._request("/route", params)

        if data and isinstance(data, list):
            _safe_log_info(f"BusproAPIParser: найдено {len(data)} маршрутов", extra={"count": len(data)})
            return data

        _safe_log_warning(f"BusproAPIParser: маршруты не найдены")
        return []

    async def get_trips(
        self,
        city_departure_id: str,
        city_destination_id: str,
        date: str,
        actual: bool = True
    ) -> List[Dict]:
        """
        Получение списка рейсов по маршруту на дату

        :param city_departure_id: ID города отправления
        :param city_destination_id: ID города назначения
        :param date: Дата в формате YYYY-MM-DD
        :param actual: Только актуальные рейсы
        :return: Список рейсов
        """
        params = {
            "s[company_id]": self.COMPANY_ID,
            "s[city_departure_id]": city_departure_id,
            "s[city_destination_id]": city_destination_id,
            "s[date_departure]": date,
        }

        if actual:
            params["actual"] = "1"

        data = await self._request("/trip", params)

        if data and isinstance(data, list):
            _safe_log_info(
                f"BusproAPIParser: найдено {len(data)} рейсов",
                extra={
                    "from": city_departure_id,
                    "to": city_destination_id,
                    "date": date,
                    "count": len(data)
                }
            )
            return data

        _safe_log_warning(f"BusproAPIParser: рейсы не найдены на {date}")
        return []

    async def get_trip(self, trip_id: int) -> Optional[Dict]:
        """
        Получение детальной информации о рейсе

        :param trip_id: ID рейса
        :return: Информация о рейсе или None
        """
        data = await self._request(f"/trip/{trip_id}")

        if data and isinstance(data, dict):
            _safe_log_info(f"BusproAPIParser: получен рейс {trip_id}")
            return data

        _safe_log_warning(f"BusproAPIParser: рейс {trip_id} не найден")
        return None

    async def get_options(self) -> Dict:
        """
        Получение настроек системы

        :return: Словарь с настройками
        """
        params = {"company": self.COMPANY_ID}
        data = await self._request("/options/get-used-options", params)

        if data and isinstance(data, dict):
            _safe_log_info("BusproAPIParser: получены настройки")
            return data

        _safe_log_warning("BusproAPIParser: не удалось получить настройки")
        return {}

    async def check_source_reservation(self, source: str = "web") -> Dict:
        """
        Проверка возможности бронирования через источник

        :param source: Источник (web)
        :return: Статус доступности
        """
        params = {"source": source, "company": self.COMPANY_ID}
        data = await self._request("/check/source-reservation", params)

        if data and isinstance(data, dict):
            _safe_log_info("BusproAPIParser: проверена возможность бронирования")
            return data

        return {"schedule": {"status": False}, "excludeSourceReservation": {"status": True}}

    def _normalize_route(self, route: Dict, from_city: str, to_city: str, date: str) -> Dict:
        """
        Нормализация данных маршрута к формату старого парсера

        :param route: Данные маршрута из API
        :param from_city: Город отправления
        :param to_city: Город назначения
        :param date: Дата
        :return: Нормализованные данные
        """
        # Определяем тип маршрута по названию
        route_name = route.get("name", "")
        via_smorgon = "Сморгонь" in route_name
        via_oshmiany = "Ошмяны" in route_name

        # Рассчитываем примерное время прибытия
        departure_time = route.get("timeDeparture", "00:00")

        # Примерная длительность в зависимости от направления
        duration_map = {
            ("Минск", "Островец"): "2 ч 25 мин",
            ("Минск", "Сморгонь"): "2 ч 5 мин",
            ("Минск", "Ошмяны"): "1 ч 50 мин",
            ("Островец", "Минск"): "2 ч 25 мин",
            ("Сморгонь", "Минск"): "2 ч 5 мин",
            ("Ошмяны", "Минск"): "1 ч 50 мин",
        }

        duration = duration_map.get((from_city, to_city), "2 ч 25 мин")

        # Расчет времени прибытия
        try:
            dep_dt = datetime.strptime(departure_time, "%H:%M")

            # Парсим длительность
            hours_match = __import__('re').search(r'(\d+)\s*ч', duration)
            minutes_match = __import__('re').search(r'(\d+)\s*мин', duration)

            total_minutes = 0
            if hours_match:
                total_minutes += int(hours_match.group(1)) * 60
            if minutes_match:
                total_minutes += int(minutes_match.group(1))

            arr_dt = dep_dt + timedelta(minutes=total_minutes)
            arrival_time = arr_dt.strftime("%H:%M")
        except Exception:
            arrival_time = departure_time

        return {
            'from_city': from_city,
            'to_city': to_city,
            'date': date,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'duration': duration,
            'price': route.get("price", 0),
            'available_seats': route.get("available_seats", 0),
            'carrier': 'Маршруточка Плюс',
            'payment_method': 'Наличные/Карта',
            'via_smorgon': via_smorgon,
            'via_oshmiany': via_oshmiany,
            'intermediate_cities': [],
            'route_type': 'via_smorgon' if via_smorgon else ('via_oshmiany' if via_oshmiany else 'direct'),
            'route_id': route.get("id"),
            'city_departure_id': route.get("cityDepartureId"),
            'city_destination_id': route.get("cityDestinationId"),
            'parsed_at': datetime.now().isoformat()
        }

    def _normalize_trip(self, trip: Dict, from_city: str, to_city: str, date: str) -> Dict:
        """
        Нормализация данных рейса к формату старого парсера

        :param trip: Данные рейса из API
        :param from_city: Город отправления
        :param to_city: Город назначения
        :param date: Дата
        :return: Нормализованные данные
        """
        # Извлекаем время отправления
        departure_time = trip.get("timeDeparture", "00:00")

        # Парсим длительность из travelTime (формат "02:25")
        travel_time = trip.get("travelTime", "02:25")
        try:
            time_parts = travel_time.split(":")
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            total_minutes = hours * 60 + minutes
            duration = f"{hours} ч {minutes} мин"
        except Exception:
            total_minutes = 145
            duration = "2 ч 25 мин"

        # Расчет времени прибытия
        try:
            dep_dt = datetime.strptime(departure_time, "%H:%M")
            arr_dt = dep_dt + timedelta(minutes=total_minutes)
            arrival_time = arr_dt.strftime("%H:%M")
        except Exception:
            arrival_time = departure_time

        # Определяем тип маршрута по названию
        route_name = trip.get("route", "")
        via_smorgon = "Сморгонь" in route_name
        via_oshmiany = "Ошмяны" in route_name

        # Количество мест: freePlaces или len(seats) если dict
        seats_data = trip.get("seats", {})
        if isinstance(seats_data, dict):
            available_seats = len(seats_data)
        elif isinstance(seats_data, int):
            available_seats = seats_data
        else:
            available_seats = trip.get("freePlaces", 0)

        return {
            'from_city': from_city,
            'to_city': to_city,
            'date': date,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'duration': duration,
            'duration_minutes': total_minutes,
            'price': trip.get("price", 0),
            'available_seats': available_seats,
            'free_places': trip.get("freePlaces", 0),
            'all_places': trip.get("allPlaces", 0),
            'carrier': 'Маршруточка Плюс',
            'payment_method': 'Наличные/Карта',
            'via_smorgon': via_smorgon,
            'via_oshmiany': via_oshmiany,
            'intermediate_cities': [],
            'route_type': 'via_smorgon' if via_smorgon else ('via_oshmiany' if via_oshmiany else 'direct'),
            'trip_id': trip.get("id"),
            'route_name': route_name,
            'driver': trip.get("driver"),
            'driver_phone': trip.get("driverPhone"),
            'transport': trip.get("transport"),
            'seats': seats_data,
            'seat_numbers': trip.get("seatNumbers", False),
            'tariff': trip.get("tariff", []),
            'stays': trip.get("stays", []),
            'finishStays': trip.get("finishStays", []),
            'parsed_at': datetime.now().isoformat()
        }

    async def search_routes(self, from_city: str, to_city: str, date: str) -> List[Dict]:
        """
        Поиск маршрутов между городами на указанную дату

        :param from_city: Город отправления
        :param to_city: Город назначения
        :param date: Дата в формате YYYY-MM-DD
        :return: Список маршрутов
        """
        from_city_id = self.CITY_IDS.get(from_city)
        to_city_id = self.CITY_IDS.get(to_city)

        if not from_city_id or not to_city_id:
            _safe_log_warning(f"BusproAPIParser: неизвестные города {from_city} -> {to_city}")
            return []

        _safe_log_info(f"BusproAPIParser: поиск маршрутов {from_city} -> {to_city} на {date}")

        # Получаем рейсы на дату
        trips = await self.get_trips(from_city_id, to_city_id, date)

        if not trips:
            _safe_log_info(f"BusproAPIParser: рейсы не найдены для {from_city} -> {to_city}")
            return []

        # Нормализуем данные
        normalized = [self._normalize_trip(trip, from_city, to_city, date) for trip in trips]

        _safe_log_info(f"BusproAPIParser: найдено {len(normalized)} маршрутов")
        return normalized

    async def get_routes_minsk_ostrovets(self, date: str) -> List[Dict]:
        """Получить маршруты Минск-Островец"""
        return await self.search_routes("Минск", "Островец", date)

    async def get_routes_ostrovets_minsk(self, date: str) -> List[Dict]:
        """Получить маршруты Островец-Минск"""
        return await self.search_routes("Островец", "Минск", date)

    async def get_routes_minsk_smorgon(self, date: str) -> List[Dict]:
        """Получить маршруты Минск-Сморгонь"""
        return await self.search_routes("Минск", "Сморгонь", date)

    async def get_routes_smorgon_minsk(self, date: str) -> List[Dict]:
        """Получить маршруты Сморгонь-Минск"""
        return await self.search_routes("Сморгонь", "Минск", date)

    async def get_routes_ostrovets_smorgon(self, date: str) -> List[Dict]:
        """Получить маршруты Островец-Сморгонь"""
        return await self.search_routes("Островец", "Сморгонь", date)

    async def get_routes_smorgon_ostrovets(self, date: str) -> List[Dict]:
        """Получить маршруты Сморгонь-Островец"""
        return await self.search_routes("Сморгонь", "Островец", date)

    async def get_all_routes(self, date: str) -> Dict[str, List[Dict]]:
        """
        Получить все маршруты в обе стороны

        :param date: Дата в формате YYYY-MM-DD
        :return: Словарь со всеми маршрутами
        """
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
            _safe_log_info("BusproAPIParser: поиск маршрутов Минск-Островец...")
            result['minsk_to_ostrovets'] = await self.get_routes_minsk_ostrovets(date)

            _safe_log_info("BusproAPIParser: поиск маршрутов Островец-Минск...")
            result['ostrovets_to_minsk'] = await self.get_routes_ostrovets_minsk(date)

            _safe_log_info("BusproAPIParser: поиск маршрутов Минск-Сморгонь...")
            result['minsk_to_smorgon'] = await self.get_routes_minsk_smorgon(date)

            _safe_log_info("BusproAPIParser: поиск маршрутов Сморгонь-Минск...")
            result['smorgon_to_minsk'] = await self.get_routes_smorgon_minsk(date)

            _safe_log_info("BusproAPIParser: поиск маршрутов Островец-Сморгонь...")
            result['ostrovets_to_smorgon'] = await self.get_routes_ostrovets_smorgon(date)

            _safe_log_info("BusproAPIParser: поиск маршрутов Сморгонь-Островец...")
            result['smorgon_to_ostrovets'] = await self.get_routes_smorgon_ostrovets(date)

            # Подсчитываем общее количество найденных маршрутов
            total_routes = sum(len(routes) for routes in result.values() if isinstance(routes, list))

            if total_routes > 0:
                result['success'] = True
                result['total_routes'] = total_routes
                _safe_log_info(f"BusproAPIParser: всего найдено {total_routes} маршрутов")
            else:
                _safe_log_warning("BusproAPIParser: маршруты не найдены")

        except Exception as e:
            _safe_log_error(f"BusproAPIParser: ошибка при получении всех маршрутов: {e}", exc_info=True)
            result['error'] = str(e)

        return result

    async def test_connection(self) -> bool:
        """
        Проверка соединения с API

        :return: True если соединение успешно
        """
        try:
            routes = await self.get_routes()
            return len(routes) > 0
        except Exception as e:
            _safe_log_error(f"BusproAPIParser: проверка соединения не удалась: {e}")
            return False


async def main():
    """Тестирование парсера"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    async with BusproAPIParser() as parser:
        # Проверка соединения
        print("🔌 Проверка соединения...")
        if await parser.test_connection():
            print("✅ Соединение успешно")
        else:
            print("❌ Соединение не удалось")
            return

        # Получаем все маршруты
        print(f"\n📅 Поиск маршрутов на {tomorrow}")
        print("=" * 60)

        routes = await parser.get_all_routes(tomorrow)

        print(f"\n✅ Статус: {'Успешно' if routes['success'] else 'Ошибка'}")
        print(f"📊 Всего маршрутов: {routes.get('total_routes', 0)}")

        print("\n🚌 Минск → Островец:")
        for route in routes['minsk_to_ostrovets']:
            print(f"   {route['departure_time']} → {route['arrival_time']} | {route['available_seats']} мест | {route['price']} BYN")

        print("\n🚌 Островец → Минск:")
        for route in routes['ostrovets_to_minsk']:
            print(f"   {route['departure_time']} → {route['arrival_time']} | {route['available_seats']} мест | {route['price']} BYN")

        print("\n🚌 Минск → Сморгонь:")
        for route in routes['minsk_to_smorgon']:
            print(f"   {route['departure_time']} → {route['arrival_time']} | {route['available_seats']} мест | {route['price']} BYN")


if __name__ == '__main__':
    asyncio.run(main())
