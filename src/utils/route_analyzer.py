#!/usr/bin/env python3
"""
Модуль для работы с маршрутами через промежуточные города (Сморгонь, Ошмяны)
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RouteAnalyzer:
    """Анализатор маршрутов для определения промежуточных городов"""
    
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
    def calculate_intermediate_arrival_time(cls, departure_time: str, route_path: List[str], target_city: str) -> Optional[str]:
        """
        Вычисляет примерное время прибытия в промежуточный город
        
        Args:
            departure_time: Время отправления (например: "10:30")
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


def generate_static_minsk_smorgon_ostrovets_schedule(date: str, real_routes: Optional[List[Dict]]) -> List[Dict]:
    """
    Генерирует статическое расписание Минск-Сморгонь-Островец с учетом реальных данных (если есть).
    Добавляет ключевые точки времени: прибытие и отправление из Сморгони.
    """
    base_departures = ["05:00", "08:00", "13:00", "18:00"]
    
    # Используем реальные данные, если доступны, иначе стандартные значения
    minsk_smorgon_minutes = RouteAnalyzer.get_average_minsk_smorgon_duration(real_routes or [])
    smorgon_ostrovets_minutes = RouteAnalyzer.get_average_smorgon_ostrovets_duration(real_routes or [])
    
    total_minutes = minsk_smorgon_minutes + smorgon_ostrovets_minutes + 5  # 5 минут стоянка в Сморгони
    
    def add_minutes(time_str: str, minutes: int) -> str:
        base_time = datetime.strptime(time_str, "%H:%M")
        return (base_time + timedelta(minutes=minutes)).strftime("%H:%M")
    
    routes: List[Dict[str, Any]] = []
    for departure in base_departures:
        smorgon_arrival = add_minutes(departure, minsk_smorgon_minutes)
        smorgon_departure = add_minutes(smorgon_arrival, 5)
        arrival_time = add_minutes(smorgon_departure, smorgon_ostrovets_minutes)
        
        routes.append({
            "date": date,
            "from_city": "Минск",
            "to_city": "Островец",
            "via_smorgon": True,
            "departure_time": departure,
            "smorgon_arrival": smorgon_arrival,
            "smorgon_departure": smorgon_departure,
            "arrival_time": arrival_time,
            "calculated_minsk_smorgon_minutes": minsk_smorgon_minutes,
            "calculated_smorgon_ostrovets_minutes": smorgon_ostrovets_minutes,
            "duration": f"~{total_minutes // 60} ч {total_minutes % 60:02d} мин",
            "route_id": f"static_{departure.replace(':', '')}",
            "route_description": "Минск-Сморгонь-Островец (стат.)"
        })
    
    return routes
