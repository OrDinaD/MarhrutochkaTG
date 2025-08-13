#!/usr/bin/env python3
"""
Тест новой функциональности поддержки маршрутов через Сморгонь
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Добавляем родительскую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.parser import FinalMarshrutochkaParser
from src.utils.route_analyzer import RouteAnalyzer, supports_smorgon_route, extract_route_details_from_site_data


async def test_smorgon_routes():
    """Тестирует функциональность маршрутов через Сморгонь"""
    
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ ПОДДЕРЖКИ МАРШРУТОВ ЧЕРЕЗ СМОРГОНЬ")
    print("=" * 70)
    
    # Тестируем анализатор маршрутов
    print("\n1. ТЕСТИРОВАНИЕ АНАЛИЗАТОРА МАРШРУТОВ")
    print("-" * 50)
    
    # Тест определения пути маршрута
    test_routes = [
        ("Минск-Сморгонь-Островец", "2 ч 25 мин"),
        ("Минск-Ошмяны-Островец", "2 ч 10 мин"),
        ("Островец-Сморгонь-Минск", "2 ч 23 мин"),
        ("Минск-Островец", "2 ч 45 мин"),  # Неизвестный тип
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
        ("Сморгонь", "Островец"),
        ("Островец", "Сморгонь"),
        ("Сморгонь", "Гродно"),  # Не поддерживается
    ]
    
    for from_city, to_city in test_routes_support:
        supported = supports_smorgon_route(from_city, to_city)
        print(f"{from_city} → {to_city}: {'✅ Поддерживается' if supported else '❌ Не поддерживается'}")
    
    print("\n4. ТЕСТИРОВАНИЕ ПАРСЕРА С НОВОЙ ФУНКЦИОНАЛЬНОСТЬЮ")
    print("-" * 50)
    
    # Получаем завтрашнюю дату
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    try:
        async with FinalMarshrutochkaParser() as parser:
            print(f"Поиск маршрутов на {tomorrow}...")
            
            # Получаем все маршруты
            all_routes = await parser.get_all_routes(tomorrow)
            
            print(f"\nРезультаты поиска:")
            print(f"Успех: {all_routes.get('success', False)}")
            print(f"Общее количество рейсов: {all_routes.get('total_routes', 0)}")
            
            # Анализируем каждое направление
            directions = [
                ('minsk_to_ostrovets', 'Минск → Островец'),
                ('ostrovets_to_minsk', 'Островец → Минск'),
                ('minsk_to_smorgon', 'Минск → Сморгонь'),
                ('smorgon_to_minsk', 'Сморгонь → Минск'),
                ('ostrovets_to_smorgon', 'Островец → Сморгонь'),
                ('smorgon_to_ostrovets', 'Сморгонь → Островец'),
            ]
            
            for direction_key, direction_name in directions:
                routes = all_routes.get(direction_key, [])
                print(f"\n{direction_name}: {len(routes)} рейсов")
                
                for i, route in enumerate(routes[:3], 1):  # Показываем первые 3
                    print(f"  {i}. {route.get('departure_time')} → {route.get('arrival_time')}")
                    print(f"     Длительность: {route.get('duration', 'н/д')}")
                    print(f"     Через Сморгонь: {route.get('via_smorgon', False)}")
                    print(f"     Через Ошмяны: {route.get('via_oshmiany', False)}")
                    print(f"     Тип маршрута: {route.get('route_type', 'unknown')}")
                    if route.get('intermediate_cities'):
                        print(f"     Промежуточные города: {', '.join(route['intermediate_cities'])}")
                    print()
    
    except Exception as e:
        print(f"Ошибка при тестировании парсера: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n5. ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ ПРЕДУПРЕЖДЕНИЯ О СМОРГОНИ")
    print("-" * 50)
    
    warning = RouteAnalyzer.generate_smorgon_warning()
    print(warning)
    
    print("\n=" * 70)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_smorgon_routes())
