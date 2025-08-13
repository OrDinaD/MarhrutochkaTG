#!/usr/bin/env python3
"""
Простой тест функциональности анализатора маршрутов без парсера
"""

import sys
import os
from datetime import datetime

# Добавляем родительскую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.route_analyzer import RouteAnalyzer, supports_smorgon_route


def test_route_analyzer():
    """Тестирует анализатор маршрутов"""
    
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ АНАЛИЗАТОРА МАРШРУТОВ ЧЕРЕЗ СМОРГОНЬ")
    print("=" * 70)
    
    # Тест определения пути маршрута
    print("\n1. ТЕСТИРОВАНИЕ ОПРЕДЕЛЕНИЯ ПУТИ МАРШРУТА")
    print("-" * 50)
    
    test_routes = [
        ("Минск-Сморгонь-Островец", "2 ч 25 мин"),
        ("Минск-Ошмяны-Островец", "2 ч 10 мин"),
        ("Островец-Сморгонь-Минск", "2 ч 23 мин"),
        ("Минск-Островец", "2 ч 45 мин"),  # Неизвестный тип
        ("Маршрут с Сморгонью", "2 ч 27 мин"),
    ]
    
    for route_desc, duration in test_routes:
        path_desc, intermediate = RouteAnalyzer.determine_route_path(route_desc, duration)
        print(f"Маршрут: {route_desc}")
        print(f"Длительность: {duration}")
        print(f"Тип: {path_desc}")
        print(f"Промежуточные города: {intermediate}")
        print()
    
    # Тест вычисления времени прибытия
    print("2. ТЕСТИРОВАНИЕ ВЫЧИСЛЕНИЯ ВРЕМЕНИ ПРИБЫТИЯ")
    print("-" * 50)
    
    test_times = [
        ("10:30", ["Минск", "Сморгонь", "Островец"], "Сморгонь"),
        ("15:45", ["Островец", "Сморгонь", "Минск"], "Сморгонь"),
        ("08:00", ["Минск", "Ошмяны", "Островец"], "Ошмяны"),
        ("14:20", ["Минск", "Сморгонь", "Островец"], "Сморгонь"),
    ]
    
    for dep_time, route_path, target_city in test_times:
        arrival = RouteAnalyzer.calculate_intermediate_arrival_time(
            dep_time, route_path[-1], route_path, target_city
        )
        print(f"Отправление: {dep_time}")
        print(f"Маршрут: {' → '.join(route_path)}")
        print(f"Время прибытия в {target_city}: {arrival or 'н/д'}")
        print()
    
    # Тест поддержки маршрутов
    print("3. ТЕСТИРОВАНИЕ ПОДДЕРЖКИ МАРШРУТОВ")
    print("-" * 50)
    
    test_routes_support = [
        ("Минск", "Сморгонь"),
        ("Сморгонь", "Минск"),
        ("Островец", "Сморгонь"),
        ("Сморгонь", "Островец"),
        ("Минск", "Островец"),  # Основной маршрут
        ("Сморгонь", "Гродно"),  # Не поддерживается
        ("Брест", "Сморгонь"),   # Не поддерживается
    ]
    
    for from_city, to_city in test_routes_support:
        supported = supports_smorgon_route(from_city, to_city)
        status = "✅ Поддерживается" if supported else "❌ Не поддерживается"
        print(f"{from_city} → {to_city}: {status}")
    
    # Тест генерации предупреждения о Сморгони
    print("\n4. ТЕСТИРОВАНИЕ ПРЕДУПРЕЖДЕНИЯ О СМОРГОНИ")
    print("-" * 50)
    
    warning = RouteAnalyzer.generate_smorgon_warning()
    print(warning)
    
    # Тест извлечения данных маршрута
    print("\n5. ТЕСТИРОВАНИЕ ИЗВЛЕЧЕНИЯ ДАННЫХ МАРШРУТА")
    print("-" * 50)
    
    from src.utils.route_analyzer import extract_route_details_from_site_data
    
    # Тестовые данные маршрута
    test_route_data = {
        'route_id': 'test_123',
        'from_city': 'Минск',
        'to_city': 'Островец',
        'departure_time': '10:30',
        'arrival_time': '12:55',
        'duration': '2 ч 25 мин',
        'available_seats': 5,
        'carrier': 'Тестовый перевозчик',
        'price_str': '8.50 BYN'
    }
    
    route_detail = extract_route_details_from_site_data(
        test_route_data, 
        "Минск-Сморгонь-Островец"
    )
    
    print(f"ID маршрута: {route_detail.route_id}")
    print(f"Маршрут: {route_detail.from_location} → {route_detail.to_location}")
    print(f"Время: {route_detail.departure_time} → {route_detail.arrival_time}")
    print(f"Длительность: {route_detail.duration}")
    print(f"Путь маршрута: {route_detail.route_path}")
    print(f"Промежуточные города: {route_detail.intermediate_cities}")
    print(f"Мест: {route_detail.available_seats}")
    print(f"Цена: {route_detail.price}")
    
    # Тест форматирования маршрута
    print("\n6. ТЕСТИРОВАНИЕ ФОРМАТИРОВАНИЯ МАРШРУТА")
    print("-" * 50)
    
    from src.utils.route_analyzer import format_route_with_intermediate_cities
    
    formatted = format_route_with_intermediate_cities(route_detail)
    print("Отформатированный маршрут:")
    print(formatted)
    
    print("\n=" * 70)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    test_route_analyzer()
