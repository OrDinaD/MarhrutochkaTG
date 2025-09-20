#!/usr/bin/env python3
"""
Модуль для работы с маршрутами через промежуточные города (Сморгонь, Ошмяны)
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RouteDetail:
    """Детальная информация о маршруте"""
    route_id: str
    from_location: str
    to_location: str
    departure_time: str
    arrival_time: str
    price: str
    available_seats: int
    bus_info: str = ""
    duration: str = ""
    route_path: str = ""  # Путь маршрута (например: "Минск-Сморгонь-Островец")
    intermediate_cities: List[str] = None
    carrier: str = ""
    
    def __post_init__(self):
        if self.intermediate_cities is None:
            self.intermediate_cities = []


class RouteAnalyzer:
    """Анализатор маршрутов для определения промежуточных городов"""
    
    # Известные маршруты и их пути
    KNOWN_ROUTES = {
        "Минск-Ошмяны-Островец": {
            "path": ["Минск", "Ошмяны", "Островец"],
            "duration_minutes": 130,  # 2ч 10 мин
            "description": "через Ошмяны"
        },
        "Минск-Сморгонь-Островец": {
            "path": ["Минск", "Сморгонь", "Островец"],
            "duration_minutes": 190,  # ~3ч 10мин (2ч 5мин + 1ч 5мин)
            "description": "через Сморгонь"
        },
        "Островец-Ошмяны-Минск": {
            "path": ["Островец", "Ошмяны", "Минск"],
            "duration_minutes": 130,
            "description": "через Ошмяны"
        },
        "Островец-Сморгонь-Минск": {
            "path": ["Островец", "Сморгонь", "Минск"],
            "duration_minutes": 190,  # ~3ч 10мин
            "description": "через Сморгонь"
        }
    }
    
    # Примерное время в пути между городами (в минутах)
    TRAVEL_TIMES = {
        ("Минск", "Сморгонь"): 125,     # ~2ч 5мин (от 1ч 55мин до 2ч 25мин - берем среднее)
        ("Сморгонь", "Островец"): 65,   # ~1ч 5мин (корректировка)
        ("Минск", "Ошмяны"): 85,       # ~1ч 25мин
        ("Ошмяны", "Островец"): 45,    # ~45мин
    }
    
    # Остановки в Сморгони (актуальная информация)
    SMORGON_STOPS = [
        "Славянка",
        "Электросети (ул. Ленина, 73)",
        "Школа №2 (ул. Ленина, 31)",
        "Ресторан \"Вилия\" (ул. Советская, 2)",
        "Школа №1 (ул. Советская, 26)",
        "Микрорайон Западный (ул. Советская, 82)"
    ]
    
    @classmethod
    def determine_route_path(cls, route_description: str, duration: str) -> Tuple[str, List[str]]:
        """
        Определяет путь маршрута на основе описания и длительности
        
        Args:
            route_description: Описание маршрута (например: "Минск-Ошмяны-Островец")
            duration: Длительность поездки (например: "2 ч 10 мин")
            
        Returns:
            Tuple[str, List[str]]: (описание пути, список промежуточных городов)
        """
        # Сначала проверяем по названию (приоритет)
        if "Сморгонь" in route_description or "сморгонь" in route_description.lower():
            if "Минск" in route_description and "Островец" in route_description:
                return "через Сморгонь", ["Сморгонь"]
        elif "Ошмяны" in route_description or "ошмяны" in route_description.lower():
            if "Минск" in route_description and "Островец" in route_description:
                return "через Ошмяны", ["Ошмяны"]
        
        # Парсим длительность
        duration_minutes = cls._parse_duration(duration)
        
        # Проверяем известные маршруты по точному совпадению
        for route_name, route_info in cls.KNOWN_ROUTES.items():
            if route_name in route_description or route_description in route_name:
                return route_info["description"], route_info["path"][1:-1]  # Промежуточные города
        
        # Если не нашли по названию, проверяем по времени в пути
        if duration_minutes:
            for route_name, route_info in cls.KNOWN_ROUTES.items():
                if abs(duration_minutes - route_info["duration_minutes"]) <= 15:
                    # Если время совпадает (+/- 15 минут), возможно это этот маршрут
                    route_cities = route_description.split('-')
                    if len(route_cities) >= 2:
                        start_city = route_cities[0].strip()
                        end_city = route_cities[-1].strip()
                        
                        route_path = route_info["path"]
                        if (route_path[0] == start_city and route_path[-1] == end_city):
                            return route_info["description"], route_path[1:-1]
        
        return "", []
    
    @classmethod
    def calculate_minsk_smorgon_duration(cls, minsk_ostrovets_route: Dict) -> Optional[int]:
        """
        Вычисляет время поездки от Минска до Сморгони на основе полного маршрута Минск-Островец
        
        Args:
            minsk_ostrovets_route: Словарь с данными маршрута Минск-Островец через Сморгонь
            
        Returns:
            Optional[int]: Время в минутах от Минска до Сморгони или None если не удалось вычислить
        """
        try:
            # Проверяем что это маршрут через Сморгонь
            if not minsk_ostrovets_route.get('via_smorgon'):
                return None
            
            # Получаем общее время поездки Минск-Островец
            duration_str = minsk_ostrovets_route.get('duration', '')
            total_duration = cls._parse_duration(duration_str)
            
            if not total_duration:
                return None
            
            # Получаем время Сморгонь-Островец (из константы)
            smorgon_ostrovets_duration = cls.TRAVEL_TIMES.get(("Сморгонь", "Островец"), 65)
            
            # Вычисляем время от Минска до Сморгони
            minsk_smorgon_duration = total_duration - smorgon_ostrovets_duration
            
            # Проверяем разумность результата (должно быть в пределах 90-150 минут)
            if 90 <= minsk_smorgon_duration <= 150:
                return minsk_smorgon_duration
            else:
                # Если результат неразумный, возвращаем стандартное значение
                return cls.TRAVEL_TIMES.get(("Минск", "Сморгонь"), 125)
                
        except Exception:
            # В случае ошибки возвращаем стандартное значение
            return cls.TRAVEL_TIMES.get(("Минск", "Сморгонь"), 125)

    @classmethod
    def get_average_minsk_smorgon_duration(cls, all_minsk_ostrovets_routes: List[Dict]) -> int:
        """
        Получает среднее время от Минска до Сморгони на основе реальных данных
        
        Args:
            all_minsk_ostrovets_routes: Список всех маршрутов Минск-Островец
            
        Returns:
            int: Средняя продолжительность в минутах (или стандартное значение если нет данных)
        """
        durations = []
        
        for route in all_minsk_ostrovets_routes:
            duration = cls.calculate_minsk_smorgon_duration(route)
            if duration:
                durations.append(duration)
        
        if durations:
            # Возвращаем среднее значение, округленное до ближайших 5 минут
            average = sum(durations) / len(durations)
            return round(average / 5) * 5
        else:
            # Если нет данных, возвращаем стандартное значение
            return cls.TRAVEL_TIMES.get(("Минск", "Сморгонь"), 125)

    @classmethod
    def get_average_smorgon_ostrovets_duration(cls, all_minsk_ostrovets_routes: List[Dict]) -> int:
        """
        Получает среднюю продолжительность поездки от Сморгони до Островца на основе реальных данных
        
        Args:
            all_minsk_ostrovets_routes: Список всех маршрутов Минск-Островец
            
        Returns:
            int: Средняя продолжительность в минутах (или стандартное значение если нет данных)
        """
        durations = []
        
        for route in all_minsk_ostrovets_routes:
            duration = cls.calculate_smorgon_ostrovets_duration(route)
            if duration:
                durations.append(duration)
        
        if durations:
            # Возвращаем среднее значение, округленное до ближайших 5 минут
            average = sum(durations) / len(durations)
            return round(average / 5) * 5
        else:
            # Если нет данных, возвращаем стандартное значение
            return cls.TRAVEL_TIMES.get(("Сморгонь", "Островец"), 65)

    @classmethod
    def calculate_smorgon_ostrovets_duration_from_routes(cls, all_minsk_ostrovets_routes: List[Dict]) -> Dict[str, int]:
        """
        Вычисляет реальное время от Сморгони до Островца на основе списка всех маршрутов Минск-Островец
        
        Args:
            all_minsk_ostrovets_routes: Список всех маршрутов Минск-Островец
            
        Returns:
            Dict[str, int]: Словарь с расчетами времени {route_id: duration_minutes}
        """
        results = {}
        
        for route in all_minsk_ostrovets_routes:
            if route.get('via_smorgon'):
                route_id = route.get('route_id', f"route_{route.get('departure_time', 'unknown')}")
                duration = cls.calculate_smorgon_ostrovets_duration(route)
                if duration:
                    results[route_id] = duration
        
        return results

    @classmethod
    def calculate_smorgon_ostrovets_duration(cls, minsk_ostrovets_route: Dict) -> Optional[int]:
        """
        Вычисляет время поездки от Сморгони до Островца на основе полного маршрута Минск-Островец
        
        Args:
            minsk_ostrovets_route: Словарь с данными маршрута Минск-Островец через Сморгонь
            
        Returns:
            Optional[int]: Время в минутах от Сморгони до Островца или None если не удалось вычислить
        """
        try:
            # Проверяем что это маршрут через Сморгонь
            if not minsk_ostrovets_route.get('via_smorgon'):
                return None
            
            # Получаем общее время поездки Минск-Островец
            duration_str = minsk_ostrovets_route.get('duration', '')
            total_duration = cls._parse_duration(duration_str)
            
            if not total_duration:
                return None
            
            # Вычитаем время Минск-Сморгонь (из константы)
            minsk_smorgon_duration = cls.TRAVEL_TIMES.get(("Минск", "Сморгонь"), 125)
            
            # Вычисляем время от Сморгони до Островца
            smorgon_ostrovets_duration = total_duration - minsk_smorgon_duration
            
            # Проверяем разумность результата (должно быть в пределах 30-90 минут)
            if 30 <= smorgon_ostrovets_duration <= 90:
                return smorgon_ostrovets_duration
            else:
                # Если результат неразумный, возвращаем стандартное значение
                return cls.TRAVEL_TIMES.get(("Сморгонь", "Островец"), 65)
                
        except Exception:
            # В случае ошибки возвращаем стандартное значение
            return cls.TRAVEL_TIMES.get(("Сморгонь", "Островец"), 65)

    @classmethod
    def _parse_duration(cls, duration_str: str) -> Optional[int]:
        """Парсит строку длительности в минуты"""
        if not duration_str:
            return None
            
        # Ищем часы и минуты
        hours_match = re.search(r'(\d+)\s*ч', duration_str)
        minutes_match = re.search(r'(\d+)\s*мин', duration_str)
        
        total_minutes = 0
        if hours_match:
            total_minutes += int(hours_match.group(1)) * 60
        if minutes_match:
            total_minutes += int(minutes_match.group(1))
            
        return total_minutes if total_minutes > 0 else None
    
    @classmethod
    def calculate_intermediate_arrival_time(cls, departure_time: str, destination_city: str, 
                                          route_path: List[str], target_city: str) -> Optional[str]:
        """
        Вычисляет примерное время прибытия в промежуточный город
        
        Args:
            departure_time: Время отправления (например: "10:30")
            destination_city: Конечный пункт маршрута
            route_path: Полный путь маршрута
            target_city: Промежуточный город, для которого нужно время
            
        Returns:
            Optional[str]: Примерное время прибытия
        """
        try:
            # Парсим время отправления
            dep_hour, dep_minute = map(int, departure_time.split(':'))
            dep_time = datetime.now().replace(hour=dep_hour, minute=dep_minute, second=0, microsecond=0)
            
            # Находим индекс целевого города в маршруте
            if target_city not in route_path:
                return None
                
            target_index = route_path.index(target_city)
            
            # Вычисляем время в пути до целевого города
            travel_minutes = 0
            for i in range(target_index):
                if i + 1 < len(route_path):
                    segment = (route_path[i], route_path[i + 1])
                    if segment in cls.TRAVEL_TIMES:
                        travel_minutes += cls.TRAVEL_TIMES[segment]
                    elif (segment[1], segment[0]) in cls.TRAVEL_TIMES:
                        travel_minutes += cls.TRAVEL_TIMES[(segment[1], segment[0])]
            
            # Добавляем время в пути к времени отправления
            if travel_minutes > 0:
                arrival_time = dep_time + timedelta(minutes=travel_minutes)
                return arrival_time.strftime("%H:%M")
                
        except Exception as e:
            logger.error(f"Ошибка вычисления времени прибытия: {e}")
            
        return None
    
    @classmethod
    def generate_smorgon_warning(cls) -> str:
        """Генерирует предупреждение об остановках в Сморгони"""
        stops_text = "\n".join([f"• {stop}" for stop in cls.SMORGON_STOPS])
        
        warning = (
            "⚠️ **Важная информация о Сморгони:**\n\n"
            "🚏 **Остановки в Сморгони:**\n"
            f"{stops_text}\n\n"
            "🕐 **Время в пути от Минска:** от 1ч 55мин до 2ч 25мин\n\n"
            "📍 **Основная остановка:** \"Школа №1\" (ул. Советская, 26)\n\n"
            "⏰ **Примерное расписание прибытия в Сморгонь:**\n"
            "• Рейс 05:00 → прибытие ~06:55-07:25\n"
            "• Рейс 08:00 → прибытие ~09:55-10:25\n"
            "• Рейс 13:00 → прибытие ~14:55-15:25\n"
            "• Рейс 18:00 → прибытие ~19:55-20:25\n\n"
            "❗ **Внимание:** Маршрутка может останавливаться не на всех остановках в Сморгони. "
            "Рекомендуется уточнить у водителя конкретную остановку при посадке.\n\n"
            "📞 **Контакты для уточнения:** +375293541000"
        )
        
        return warning


def extract_route_details_from_site_data(route_data: Dict, route_description: str = "") -> RouteDetail:
    """
    Извлекает детальную информацию о маршруте из данных сайта
    
    Args:
        route_data: Данные маршрута с сайта
        route_description: Описание маршрута (если доступно)
        
    Returns:
        RouteDetail: Объект с детальной информацией
    """
    duration = route_data.get('duration', '')
    route_path_desc, intermediate_cities = RouteAnalyzer.determine_route_path(
        route_description, duration
    )
    
    return RouteDetail(
        route_id=route_data.get('route_id', ''),
        from_location=route_data.get('from_city', ''),
        to_location=route_data.get('to_city', ''),
        departure_time=route_data.get('departure_time', ''),
        arrival_time=route_data.get('arrival_time', ''),
        price=route_data.get('price_str', ''),
        available_seats=route_data.get('available_seats', 0),
        bus_info=route_data.get('carrier', ''),
        duration=duration,
        route_path=route_path_desc,
        intermediate_cities=intermediate_cities,
        carrier=route_data.get('carrier', '')
    )


def supports_smorgon_route(from_city: str, to_city: str) -> bool:
    """
    Проверяет, поддерживается ли маршрут через Сморгонь
    
    Args:
        from_city: Город отправления
        to_city: Город назначения
        
    Returns:
        bool: True если маршрут поддерживается
    """
    supported_routes = [
        ("Минск", "Сморгонь"),
        ("Сморгонь", "Минск"),
        ("Островец", "Сморгонь"),
        ("Сморгонь", "Островец"),
        # Транзитные маршруты через Сморгонь
        ("Минск", "Островец"),  # может идти через Сморгонь
        ("Островец", "Минск")   # может идти через Сморгонь
    ]
    
    return (from_city, to_city) in supported_routes


def format_route_with_intermediate_cities(route_detail: RouteDetail) -> str:
    """
    Форматирует информацию о маршруте с указанием промежуточных городов
    
    Args:
        route_detail: Детальная информация о маршруте
        
    Returns:
        str: Отформатированная строка с информацией о маршруте
    """
    # Базовая информация
    route_info = [
        f"🚌 **{route_detail.departure_time} → {route_detail.arrival_time}** ({route_detail.duration})"
    ]
    
    # Проверяем, нужно ли показывать места (для Сморгонь-Островец не показываем)
    is_smorgon_to_ostrovets = (route_detail.from_location == "Сморгонь" and 
                              route_detail.to_location == "Островец")
    
    if not is_smorgon_to_ostrovets and route_detail.available_seats is not None:
        seats_emoji = "🚫" if route_detail.available_seats == 0 else "🔥" if route_detail.available_seats <= 3 else "✅"
        route_info.append(f"{seats_emoji} **{route_detail.available_seats} мест** • {route_detail.price}")
    elif route_detail.price:
        route_info.append(f"💰 **{route_detail.price}**")
    
    # Добавляем информацию о пути маршрута
    if route_detail.route_path:
        route_info.append(f"🛣️ **Маршрут:** {route_detail.route_path}")
    
    # Добавляем информацию о промежуточных городах
    if route_detail.intermediate_cities:
        if "Сморгонь" in route_detail.intermediate_cities:
            # Вычисляем примерное время прибытия в Сморгонь
            full_route_path = [route_detail.from_location] + route_detail.intermediate_cities + [route_detail.to_location]
            smorgon_arrival = RouteAnalyzer.calculate_intermediate_arrival_time(
                route_detail.departure_time,
                route_detail.to_location,
                full_route_path,
                "Сморгонь"
            )
            
            if smorgon_arrival:
                route_info.append(f"🏙️ **Сморгонь:** ~{smorgon_arrival}")
    
    # Добавляем перевозчика
    if route_detail.carrier:
        route_info.append(f"🚌 **{route_detail.carrier}**")
    
    # Специальное примечание для маршрутов от Сморгони
    if is_smorgon_to_ostrovets:
        route_info.append("✅ **Всех берут** (места не ограничены)")
    
    return "\n".join(route_info)


def generate_static_minsk_smorgon_ostrovets_schedule(search_date: str, real_routes_data: List[Dict] = None) -> List[Dict]:
    """
    Генерирует статическое расписание для маршрута Минск-Сморгонь-Островец
    
    Args:
        search_date: Дата поиска в формате YYYY-MM-DD
        real_routes_data: Реальные данные маршрутов для расчета времени (опционально)
        
    Returns:
        List[Dict]: Список маршрутов с информацией о времени и ценах
    """
    from datetime import datetime, timedelta
    
    # Фиксированные времена отправления из Минска через Сморгонь
    minsk_departure_times = [
        "07:00", "07:30", "08:30", "09:30", "10:00", 
        "11:00", "12:00", "13:30", "14:30", "15:30", 
        "16:30", "18:00", "19:00", "21:00"
    ]
    
    # Если есть реальные данные, используем их для расчета времени
    if real_routes_data:
        avg_minsk_smorgon_duration = RouteAnalyzer.get_average_minsk_smorgon_duration(real_routes_data)
        avg_smorgon_ostrovets_duration = RouteAnalyzer.get_average_smorgon_ostrovets_duration(real_routes_data)
    else:
        # Используем стандартные значения
        avg_minsk_smorgon_duration = RouteAnalyzer.TRAVEL_TIMES.get(("Минск", "Сморгонь"), 125)
        avg_smorgon_ostrovets_duration = RouteAnalyzer.TRAVEL_TIMES.get(("Сморгонь", "Островец"), 65)
    
    routes = []
    current_time = datetime.now()
    search_datetime = datetime.strptime(search_date, "%Y-%m-%d")
    is_today = search_datetime.date() == current_time.date()
    
    for i, departure_time in enumerate(minsk_departure_times, 1):
        # Вычисляем время прибытия в Сморгонь (используем динамические данные)
        dep_hour, dep_minute = map(int, departure_time.split(':'))
        dep_dt = datetime.now().replace(hour=dep_hour, minute=dep_minute, second=0)
        smorgon_arrival_dt = dep_dt + timedelta(minutes=avg_minsk_smorgon_duration)
        
        # Вычисляем время отправления из Сморгони в Островец (через 5 минут)
        smorgon_departure_dt = smorgon_arrival_dt + timedelta(minutes=5)
        
        # Вычисляем время прибытия в Островец (используем динамические данные)
        ostrovets_arrival_dt = smorgon_departure_dt + timedelta(minutes=avg_smorgon_ostrovets_duration)
        
        # Если ищем на сегодня, пропускаем уже ушедшие рейсы
        # Проверяем, что рейс еще не дошел до Островца
        if is_today and ostrovets_arrival_dt.time() <= current_time.time():
            continue
        
        # Рассчитываем общую продолжительность
        total_duration = avg_minsk_smorgon_duration + 5 + avg_smorgon_ostrovets_duration
        total_hours = total_duration // 60
        total_minutes = total_duration % 60
        duration_str = f"{total_hours}ч {total_minutes}мин" if total_hours > 0 else f"{total_minutes}мин"
        
        route = {
            'route_id': f'static_minsk_smorgon_ostrovets_{i}',
            'from_city': 'Минск',
            'to_city': 'Островец',
            'departure_time': departure_time,
            'arrival_time': ostrovets_arrival_dt.strftime("%H:%M"),
            'duration': duration_str,
            'price_str': '8,00 руб.',
            'available_seats': None,  # Места не ограничены
            'carrier': 'Маршрутное такси',
            'via_smorgon': True,
            'smorgon_arrival': smorgon_arrival_dt.strftime("%H:%M"),
            'smorgon_departure': smorgon_departure_dt.strftime("%H:%M"),
            'is_static_route': True,
            'calculated_minsk_smorgon_minutes': avg_minsk_smorgon_duration,
            'calculated_smorgon_ostrovets_minutes': avg_smorgon_ostrovets_duration
        }
        routes.append(route)
    
    return routes
