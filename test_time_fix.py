#!/usr/bin/env python3
"""
Тест для проверки исправления диапазона времени
"""

import re
from datetime import datetime

def test_time_range_validation():
    """Тестируем валидацию диапазона времени"""
    
    def validate_time_range(text):
        """Функция валидации как в боте"""
        if not re.match(r'^\d{2}:\d{2}-\d{2}:\d{2}$', text):
            return False, "Неверный формат"
        
        try:
            time_parts = text.split('-')
            start_time = time_parts[0]
            end_time = time_parts[1]
            
            # Проверяем формат времени
            start_hour, start_min = map(int, start_time.split(':'))
            end_hour, end_min = map(int, end_time.split(':'))
            
            if not (0 <= start_hour <= 23 and 0 <= start_min <= 59 and 
                   0 <= end_hour <= 23 and 0 <= end_min <= 59):
                return False, "Неверное время"
            
            # Проверяем, что начальное время меньше конечного
            if start_hour * 60 + start_min >= end_hour * 60 + end_min:
                return False, "Время начала должно быть раньше времени окончания"
            
            return True, "OK"
            
        except ValueError:
            return False, "Ошибка парсинга"
    
    # Тестовые случаи
    test_cases = [
        ("07:00-09:00", True, "Правильный диапазон"),
        ("17:30-19:30", True, "Правильный диапазон с минутами"),
        ("23:59-23:58", False, "Начало позже конца"),
        ("10:00-10:00", False, "Одинаковое время"),
        ("25:00-09:00", False, "Неверный час"),
        ("07:60-09:00", False, "Неверные минуты"),
        ("7:00-9:00", False, "Неверный формат (без ведущего нуля)"),
        ("07:00-9:00", False, "Неверный формат конечного времени"),
        ("abc-def", False, "Текст вместо времени"),
        ("", False, "Пустая строка"),
    ]
    
    print("🕐 Тестирование валидации диапазона времени\n")
    
    for test_input, expected_valid, description in test_cases:
        is_valid, message = validate_time_range(test_input)
        status = "✅" if is_valid == expected_valid else "❌"
        
        print(f"{status} {test_input:15} | {description}")
        if not (is_valid == expected_valid):
            print(f"   Ожидалось: {expected_valid}, получено: {is_valid} ({message})")
    
    print("\n" + "="*50)
    print("✅ Тест завершен!")

if __name__ == "__main__":
    test_time_range_validation()
