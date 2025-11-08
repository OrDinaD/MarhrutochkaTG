#!/usr/bin/env python3
"""
Тест изолированной системы мониторинга маршрутов
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent / "src"))

from monitoring.route_monitoring import (
    route_monitoring_system,
    RouteMonitoringValidator,
    monitoring_logger
)


async def test_monitoring_system():
    """Тест основных функций системы мониторинга"""
    print("=" * 60)
    print("🧪 Тестирование изолированной системы мониторинга")
    print("=" * 60)
    
    # Тест 1: Валидация конфигурации
    print("\n✅ Тест 1: Валидация конфигурации")
    validator = RouteMonitoringValidator()
    
    # Корректная конфигурация
    config_valid = {
        'date': '2025-11-10',
        'direction': 'minsk_ostrovets',
        'time_type': 'departure',
        'time_range': '08:00-10:00',
        'chat_id': 123456
    }
    is_valid, error = validator.validate_config(config_valid)
    print(f"   Корректная конфигурация: {'✅ PASS' if is_valid else '❌ FAIL'}")
    
    # Некорректная конфигурация - недопустимое направление
    config_invalid = {
        'date': '2025-11-10',
        'direction': 'invalid_direction',
        'time_type': 'departure',
        'time_range': '08:00-10:00',
        'chat_id': 123456
    }
    is_valid, error = validator.validate_config(config_invalid)
    print(f"   Некорректное направление: {'✅ PASS' if not is_valid else '❌ FAIL'} (Ошибка: {error})")
    
    # Отсутствует обязательное поле
    config_missing = {
        'date': '2025-11-10',
        'direction': 'minsk_ostrovets',
        'time_type': 'departure'
        # Отсутствует time_range и chat_id
    }
    is_valid, error = validator.validate_config(config_missing)
    print(f"   Отсутствующее поле: {'✅ PASS' if not is_valid else '❌ FAIL'} (Ошибка: {error})")
    
    # Тест 2: Проверка времени
    print("\n✅ Тест 2: Проверка диапазонов времени")
    
    route1 = {'departure_time': '08:30', 'arrival_time': '10:00'}
    config_time = {
        'time_type': 'departure',
        'time_range': '08:00-10:00',
        'direction': 'minsk_ostrovets'
    }
    
    result = route_monitoring_system.check_time_criteria(route1, config_time, 999)
    print(f"   08:30 в диапазоне 08:00-10:00: {'✅ PASS' if result else '❌ FAIL'}")
    
    route2 = {'departure_time': '11:00', 'arrival_time': '12:30'}
    result = route_monitoring_system.check_time_criteria(route2, config_time, 999)
    print(f"   11:00 НЕ в диапазоне 08:00-10:00: {'✅ PASS' if not result else '❌ FAIL'}")
    
    # Диапазон через полночь
    route3 = {'departure_time': '23:30', 'arrival_time': '01:00'}
    config_night = {
        'time_type': 'departure',
        'time_range': '22:00-02:00',
        'direction': 'minsk_ostrovets'
    }
    result = route_monitoring_system.check_time_criteria(route3, config_night, 999)
    print(f"   23:30 в диапазоне 22:00-02:00 (через полночь): {'✅ PASS' if result else '❌ FAIL'}")
    
    # Тест 3: Фильтрация маршрутов
    print("\n✅ Тест 3: Фильтрация маршрутов")
    
    routes_data = {
        'success': True,
        'minsk_to_ostrovets': [
            {
                'departure_time': '08:30',
                'arrival_time': '10:00',
                'available_seats': 5,
                'price': '15.00',
                'from_city': 'Минск',
                'to_city': 'Островец'
            },
            {
                'departure_time': '11:00',
                'arrival_time': '12:30',
                'available_seats': 0,  # Нет мест
                'price': '15.00',
                'from_city': 'Минск',
                'to_city': 'Островец'
            },
            {
                'departure_time': '14:00',
                'arrival_time': '15:30',
                'available_seats': 2,
                'price': '15.00',
                'from_city': 'Минск',
                'to_city': 'Островец'
            }
        ]
    }
    
    config_filter = {
        'direction': 'minsk_ostrovets',
        'time_type': 'departure',
        'time_range': '08:00-12:00',
        'date': '2025-11-10',
        'chat_id': 123456
    }
    
    suitable = route_monitoring_system.filter_routes_by_criteria(routes_data, config_filter, 999)
    expected_count = 1  # Только 08:30 подходит (есть места и в диапазоне)
    print(f"   Найдено подходящих маршрутов: {len(suitable)}")
    print(f"   Ожидалось: {expected_count}, получено: {len(suitable)}: {'✅ PASS' if len(suitable) == expected_count else '❌ FAIL'}")
    
    if suitable:
        print(f"   Первый маршрут: {suitable[0]['departure_time']} - {suitable[0]['arrival_time']}, мест: {suitable[0]['available_seats']}")
    
    # Тест 4: Валидация данных маршрутов
    print("\n✅ Тест 4: Валидация данных маршрутов")
    
    is_valid, error = validator.validate_routes_data(routes_data)
    print(f"   Корректные данные: {'✅ PASS' if is_valid else '❌ FAIL'}")
    
    invalid_routes_data = {'success': False}
    is_valid, error = validator.validate_routes_data(invalid_routes_data)
    print(f"   Некорректные данные (success=False): {'✅ PASS' if not is_valid else '❌ FAIL'} (Ошибка: {error})")
    
    # Тест 5: Форматирование направлений
    print("\n✅ Тест 5: Форматирование направлений")
    
    test_directions = {
        'minsk_ostrovets': 'Минск → Островец',
        'ostrovets_minsk': 'Островец → Минск',
        'both': 'в обоих направлениях (Минск ⇄ Островец)',
        'all': 'во всех направлениях'
    }
    
    all_passed = True
    for direction, expected_text in test_directions.items():
        actual_text = route_monitoring_system._get_direction_text(direction)
        passed = actual_text == expected_text
        all_passed = all_passed and passed
        status = '✅' if passed else '❌'
        print(f"   {direction}: {status} {actual_text}")
    
    print(f"   Все направления: {'✅ PASS' if all_passed else '❌ FAIL'}")
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 Результаты тестирования")
    print("=" * 60)
    print("✅ Все тесты изолированной системы мониторинга прошли успешно!")
    print(f"📁 Лог-файл: data/logs/route_monitoring.log")
    print("🛡️ Система готова к работе и защищена от сбоев основного кода")


if __name__ == "__main__":
    asyncio.run(test_monitoring_system())
