#!/usr/bin/env python3
"""
Простая проверка корректности изменений
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_imports():
    """Проверка импортов"""
    print("✓ Проверка импортов...")
    
    try:
        from monitoring.route_monitoring import (
            RouteMonitoringValidator,
            RouteMonitoringSystem,
            route_monitoring_system
        )
        print("  ✓ route_monitoring импортирован успешно")
    except Exception as e:
        print(f"  ✗ Ошибка импорта route_monitoring: {e}")
        return False
    
    try:
        from utils.keyboards import keyboard_factory
        print("  ✓ keyboards импортирован успешно")
    except Exception as e:
        print(f"  ✗ Ошибка импорта keyboards: {e}")
        return False
    
    return True

def test_validator():
    """Проверка валидатора"""
    print("\n✓ Проверка валидатора...")
    
    from monitoring.route_monitoring import RouteMonitoringValidator
    
    validator = RouteMonitoringValidator()
    
    # Тест 1: Корректная конфигурация
    config_ok = {
        'date': '2025-01-15',
        'direction': 'minsk_ostrovets',
        'time_type': 'departure',
        'time_range': '07:00-09:00',
        'chat_id': 123456
    }
    
    is_valid, error = validator.validate_config(config_ok)
    if is_valid:
        print("  ✓ Валидация корректной конфигурации прошла")
    else:
        print(f"  ✗ Ошибка валидации: {error}")
        return False
    
    # Тест 2: Проверка, что 'both' не поддерживается
    config_both = config_ok.copy()
    config_both['direction'] = 'both'
    
    is_valid, error = validator.validate_config(config_both)
    if not is_valid and 'направление' in error.lower():
        print("  ✓ Направление 'both' корректно отклонено")
    else:
        print(f"  ✗ Направление 'both' не было отклонено")
        return False
    
    # Тест 3: Проверка автоматической остановки
    from datetime import datetime, timedelta
    
    config_past = config_ok.copy()
    config_past['date'] = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    should_stop, reason = validator.should_monitoring_stop(config_past)
    if should_stop:
        print(f"  ✓ Автоматическая остановка для прошедшей даты работает")
        print(f"    Причина: {reason}")
    else:
        print(f"  ✗ Автоматическая остановка не сработала")
        return False
    
    return True

def test_keyboards():
    """Проверка клавиатур"""
    print("\n✓ Проверка клавиатур...")
    
    from utils.keyboards import keyboard_factory
    
    # Проверяем, что клавиатура направлений не содержит 'both'
    direction_keyboard = keyboard_factory.get_direction_keyboard()
    
    # Проверяем текст кнопок
    has_both = False
    for row in direction_keyboard.inline_keyboard:
        for button in row:
            if 'оба' in button.text.lower():
                has_both = True
                break
    
    if not has_both:
        print("  ✓ Кнопка 'Оба направления' успешно удалена")
    else:
        print("  ✗ Кнопка 'Оба направления' все еще присутствует")
        return False
    
    return True

def test_monitoring_system():
    """Проверка системы мониторинга"""
    print("\n✓ Проверка системы мониторинга...")
    
    from monitoring.route_monitoring import RouteMonitoringSystem
    
    system = RouteMonitoringSystem()
    
    # Проверяем наличие новых методов
    if hasattr(system, 'send_monitoring_stopped_notification'):
        print("  ✓ Метод send_monitoring_stopped_notification присутствует")
    else:
        print("  ✗ Метод send_monitoring_stopped_notification отсутствует")
        return False
    
    # Проверяем _get_direction_text без 'both'
    direction_text = system._get_direction_text('both')
    if direction_text == 'both':  # Должен вернуть как есть, без перевода
        print("  ✓ Направление 'both' больше не переводится")
    else:
        print(f"  ✗ Направление 'both' имеет перевод: {direction_text}")
        return False
    
    return True

def main():
    """Основная функция проверки"""
    print("=" * 60)
    print("ПРОВЕРКА УЛУЧШЕНИЙ СИСТЕМЫ МОНИТОРИНГА")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_imports()
    all_passed &= test_validator()
    all_passed &= test_keyboards()
    all_passed &= test_monitoring_system()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО")
        print("=" * 60)
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОШЛИ")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
