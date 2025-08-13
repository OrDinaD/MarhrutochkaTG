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
            "duration_minutes": 145,  # 2ч 25 мин
            "description": "через Сморгонь"
        },
        "Островец-Ошмяны-Минск": {
            "path": ["Островец", "Ошмяны", "Минск"],
            "duration_minutes": 130,
            "description": "через Ошмяны"
        },
        "Островец-Сморгонь-Минск": {
            "path": ["Островец", "Сморгонь", "Минск"],
            "duration_minutes": 145,
            "description": "через Сморгонь"
        }
    }
    
    # Примерное время в пути между городами (в минутах)
    TRAVEL_TIMES = {
        ("Минск", "Сморгонь"): 75,      # ~1ч 15мин
        ("Сморгонь", "Островец"): 70,    # ~1ч 10мин
        ("Минск", "Ошмяны"): 85,        # ~1ч 25мин
        ("Ошмяны", "Островец"): 45,     # ~45мин
    }
    
    # Остановки в Сморгони (из изученного сайта)
    SMORGON_STOPS = [
        "Автобусная ост. Инженерная",
        "Автобусная ост. Гостиница", 
        "Автобусная ост. Колосок",
        "Автобусная ост. Вещевой рынок",
        "Автобусная ост. Литейный завод",
        "Авт. ост. \"Площадь 17 сентября\" (улица Советская,125)"
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
    seats_emoji = "🚫" if route_detail.available_seats == 0 else "🔥" if route_detail.available_seats <= 3 else "✅"
    
    route_info = [
        f"🕐 **{route_detail.departure_time} → {route_detail.arrival_time}** ({route_detail.duration})",
        f"{seats_emoji} **{route_detail.available_seats} мест** • {route_detail.price}",
    ]
    
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
    
    return "\n".join(route_info)
