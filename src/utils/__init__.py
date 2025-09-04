"""
Утилиты для бота
"""

from .parser import FinalMarshrutochkaParser

# Добавляем недостающие функции как заглушки
def parse_route_data(data):
    """Парсинг данных маршрутов (заглушка)"""
    return data

def parse_schedule_data(data):
    """Парсинг данных расписания (заглушка)"""
    return data

def format_routes_message(routes_data, date=None, direction='both'):
    """Форматирование сообщения с рейсами"""
    if not routes_data:
        return "❌ Рейсы не найдены"
    
    message = f"🚌 **Рейсы на {date or 'выбранную дату'}**\n\n"
    
    if isinstance(routes_data, list):
        for i, route in enumerate(routes_data[:5], 1):
            message += f"{i}. {route.get('departure_time', '00:00')} → {route.get('arrival_time', '00:00')}\n"
    else:
        message += "Данные загружены\n"
    
    return message

def format_route_details(route_data):
    """Форматирование детальной информации о рейсе"""
    if not route_data:
        return "❌ Нет данных о рейсе"
    
    return f"🚌 **Детали рейса**\n{route_data}"

__all__ = [
    'FinalMarshrutochkaParser',
    'parse_route_data',
    'parse_schedule_data', 
    'format_routes_message',
    'format_route_details'
]
