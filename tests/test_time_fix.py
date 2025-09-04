#!/usr/bin/env python3
"""
Тесты для валидации диапазона времени
"""

import pytest
import re
from datetime import datetime, time


class TestTimeValidation:
    """Тесты валидации времени и диапазонов"""
    
    def validate_time_range(self, text):
        """Функция валидации диапазона времени"""
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
    
    @pytest.mark.parametrize("time_range,expected_valid,description", [
        ("07:00-09:00", True, "Правильный диапазон"),
        ("17:30-19:30", True, "Правильный диапазон с минутами"),
        ("00:00-23:59", True, "Максимальный диапазон"),
        ("12:00-12:01", True, "Минимальный диапазон в 1 минуту"),
        ("23:59-23:58", False, "Начало позже конца"),
        ("10:00-10:00", False, "Одинаковое время"),
        ("25:00-09:00", False, "Неверный час начала"),
        ("07:00-25:00", False, "Неверный час конца"),
        ("07:60-09:00", False, "Неверные минуты начала"),
        ("07:00-09:60", False, "Неверные минуты конца"),
        ("7:00-9:00", False, "Неверный формат (без ведущего нуля)"),
        ("07:00-9:00", False, "Неверный формат конечного времени"),
        ("abc-def", False, "Текст вместо времени"),
        ("", False, "Пустая строка"),
        ("07:00", False, "Отсутствует конечное время"),
        ("07:00-", False, "Отсутствует время после дефиса"),
        ("-09:00", False, "Отсутствует время до дефиса"),
    ])
    def test_time_range_validation(self, time_range, expected_valid, description):
        """Тестирует валидацию диапазона времени с различными входными данными"""
        
        is_valid, message = self.validate_time_range(time_range)
        
        assert is_valid == expected_valid, f"{description}: ожидалось {expected_valid}, получено {is_valid} ({message})"
    
    def test_time_format_validation(self):
        """Тестирует валидацию формата времени"""
        
        valid_formats = ["00:00", "12:30", "23:59"]
        invalid_formats = ["24:00", "12:60", "ab:cd", "1:30", "12:5"]
        
        time_pattern = re.compile(r'^\d{2}:\d{2}$')
        
        for time_str in valid_formats:
            assert time_pattern.match(time_str), f"Время {time_str} должно быть валидным"
            
            # Дополнительная проверка парсинга
            try:
                hour, minute = map(int, time_str.split(':'))
                assert 0 <= hour <= 23 and 0 <= minute <= 59
            except ValueError:
                pytest.fail(f"Не удалось распарсить время {time_str}")
        
        for time_str in invalid_formats:
            if time_pattern.match(time_str):
                # Если формат правильный, проверяем значения
                try:
                    hour, minute = map(int, time_str.split(':'))
                    assert not (0 <= hour <= 23 and 0 <= minute <= 59), f"Время {time_str} должно быть невалидным"
                except ValueError:
                    pass  # Ошибка парсинга ожидаема
            # Если формат неправильный, это тоже нормально
    
    def test_time_comparison(self):
        """Тестирует сравнение времени"""
        
        test_cases = [
            ("08:00", "09:00", True),   # 08:00 < 09:00
            ("12:30", "12:31", True),   # 12:30 < 12:31
            ("09:00", "08:00", False),  # 09:00 > 08:00
            ("12:30", "12:30", False),  # 12:30 == 12:30
            ("23:59", "00:00", False),  # 23:59 > 00:00 (в рамках одного дня)
        ]
        
        for start_str, end_str, should_be_less in test_cases:
            start_hour, start_min = map(int, start_str.split(':'))
            end_hour, end_min = map(int, end_str.split(':'))
            
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min
            
            is_less = start_minutes < end_minutes
            
            assert is_less == should_be_less, f"{start_str} < {end_str} должно быть {should_be_less}"
    
    def test_time_range_edge_cases(self):
        """Тестирует граничные случаи для диапазона времени"""
        
        edge_cases = [
            ("00:00-00:01", True),   # Минимальный диапазон
            ("23:58-23:59", True),   # Диапазон в конце дня
            ("00:00-23:59", True),   # Весь день
            ("12:00-12:00", False),  # Нулевой диапазон
            ("23:59-00:00", False),  # Переход через полночь (в рамках одного дня)
        ]
        
        for time_range, expected in edge_cases:
            is_valid, _ = self.validate_time_range(time_range)
            assert is_valid == expected, f"Диапазон {time_range} должен быть {'валидным' if expected else 'невалидным'}"
    
    def test_time_parsing_error_handling(self):
        """Тестирует обработку ошибок при парсинге времени"""
        
        error_cases = [
            "abc:def-ghi:jkl",
            "12-34:56:78",
            "1a:2b-3c:4d",
            "12::34-56::78"
        ]
        
        for time_range in error_cases:
            is_valid, message = self.validate_time_range(time_range)
            assert not is_valid, f"Некорректный диапазон {time_range} должен быть невалидным"
            assert "ошибка" in message.lower() or "неверн" in message.lower(), f"Должно быть сообщение об ошибке для {time_range}"
