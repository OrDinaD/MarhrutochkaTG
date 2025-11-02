#!/usr/bin/env python3
"""
Тесты для модуля безопасности
"""

import pytest
from src.security import SecurityValidator


class TestSecurityValidator:
    """Тесты валидатора безопасности"""
    
    def test_validate_phone_valid_formats(self):
        """Тест валидации корректных форматов телефона"""
        validator = SecurityValidator()
        
        # Различные корректные форматы
        valid_phones = [
            '+375291234567',
            '375291234567',
            '291234567',
            '+375 29 123 45 67',
            '+375-29-123-45-67'
        ]
        
        for phone in valid_phones:
            assert validator.validate_phone(phone) is True, f"Должен пройти валидацию: {phone}"
    
    def test_validate_phone_invalid_formats(self):
        """Тест валидации некорректных форматов телефона"""
        validator = SecurityValidator()
        
        invalid_phones = [
            '',
            None,
            '123',  # Слишком короткий
            '+1234567890123456',  # Слишком длинный
            'abcdefghijk',  # Буквы
            '+380291234567',  # Украинский код
            '+7291234567'  # Российский код
        ]
        
        for phone in invalid_phones:
            assert validator.validate_phone(phone) is False, f"Не должен пройти валидацию: {phone}"
    
    def test_sanitize_input_basic(self):
        """Тест базовой санитизации ввода"""
        validator = SecurityValidator()
        
        # Обычный текст
        text = "Привет, мир!"
        result = validator.sanitize_input(text)
        assert result == "Привет, мир!"
    
    def test_sanitize_input_html_escape(self):
        """Тест экранирования HTML символов"""
        validator = SecurityValidator()
        
        # Текст с HTML
        text = "<script>alert('xss')</script>"
        result = validator.sanitize_input(text)
        
        # HTML символы должны быть удалены
        assert "<" not in result
        assert ">" not in result
    
    def test_sanitize_input_max_length(self):
        """Тест ограничения длины текста"""
        validator = SecurityValidator()
        
        # Длинный текст
        long_text = "a" * 2000
        result = validator.sanitize_input(long_text, max_length=100)
        
        assert len(result) <= 100
    
    def test_sanitize_input_empty(self):
        """Тест санитизации пустого ввода"""
        validator = SecurityValidator()
        
        assert validator.sanitize_input("") == ""
        assert validator.sanitize_input(None) == ""
        assert validator.sanitize_input("   ") == ""
    
    def test_sanitize_input_dangerous_chars(self):
        """Тест удаления опасных символов"""
        validator = SecurityValidator()
        
        dangerous = "Test<>\"'data"
        result = validator.sanitize_input(dangerous)
        
        # Опасные символы должны быть удалены
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert "'" not in result
    
    def test_validate_date_valid_formats(self):
        """Тест валидации корректных дат"""
        validator = SecurityValidator()
        
        valid_dates = [
            '2025-11-03',
            '2025-01-01',
            '2025-12-31',
            '2024-02-29'  # Високосный год
        ]
        
        for date_str in valid_dates:
            assert validator.validate_date(date_str) is True, f"Должна пройти валидацию: {date_str}"
    
    def test_validate_date_invalid_formats(self):
        """Тест валидации некорректных дат"""
        validator = SecurityValidator()
        
        invalid_dates = [
            '',
            None,
            '2025/11/03',  # Неправильный формат
            '03-11-2025',  # Неправильный порядок
            '2025-13-01',  # Несуществующий месяц
            '2025-02-30',  # Несуществующий день
            '2023-02-29',  # Не високосный год
            'abc'
        ]
        
        for date_str in invalid_dates:
            assert validator.validate_date(date_str) is False, f"Не должна пройти валидацию: {date_str}"
    
    def test_validate_time_range_valid(self):
        """Тест валидации корректных временных диапазонов"""
        validator = SecurityValidator()
        
        valid_ranges = [
            '05:00-09:00',
            '09:00-15:00',
            '15:00-20:00',
            '00:00-23:59'
        ]
        
        for time_range in valid_ranges:
            assert validator.validate_time_range(time_range) is True, f"Должен пройти валидацию: {time_range}"
    
    def test_validate_time_range_invalid(self):
        """Тест валидации некорректных временных диапазонов"""
        validator = SecurityValidator()
        
        invalid_ranges = [
            '',
            None,
            '25:00-26:00',  # Неправильные часы
            '10:70-11:00',  # Неправильные минуты
            '10:00',  # Отсутствует диапазон
            'abc-def',
            '10:00-10:00'  # Начало равно концу
        ]
        
        for time_range in invalid_ranges:
            assert validator.validate_time_range(time_range) is False, f"Не должен пройти валидацию: {time_range}"


class TestSecurityEdgeCases:
    """Тесты граничных случаев безопасности"""
    
    def test_sanitize_unicode_characters(self):
        """Тест санитизации юникод символов"""
        validator = SecurityValidator()
        
        # Эмодзи и специальные символы
        text = "Привет 👋 мир 🌍!"
        result = validator.sanitize_input(text)
        
        # Юникод должен сохраниться
        assert "👋" in result
        assert "🌍" in result
    
    def test_sanitize_sql_injection_attempt(self):
        """Тест защиты от SQL инъекций"""
        validator = SecurityValidator()
        
        sql_injection = "'; DROP TABLE users; --"
        result = validator.sanitize_input(sql_injection)
        
        # Опасные символы должны быть удалены
        assert "'" not in result
        assert '"' not in result
    
    def test_phone_with_spaces_and_dashes(self):
        """Тест телефона с пробелами и дефисами"""
        validator = SecurityValidator()
        
        phone = "+375 29 123-45-67"
        assert validator.validate_phone(phone) is True
    
    def test_sanitize_very_long_input(self):
        """Тест санитизации очень длинного ввода"""
        validator = SecurityValidator()
        
        very_long = "x" * 100000
        result = validator.sanitize_input(very_long, max_length=1000)
        
        assert len(result) == 1000
    
    def test_validate_date_boundary_values(self):
        """Тест граничных значений дат"""
        validator = SecurityValidator()
        
        # Граничные случаи
        assert validator.validate_date('2025-01-01') is True  # Начало года
        assert validator.validate_date('2025-12-31') is True  # Конец года
        assert validator.validate_date('2024-02-29') is True  # Високосный год
        assert validator.validate_date('2025-02-29') is False  # Не високосный год
    
    def test_sanitize_input_non_string(self):
        """Тест санитизации не-строковых типов"""
        validator = SecurityValidator()
        
        # Числа, списки и т.д.
        assert validator.sanitize_input(123) == ""
        assert validator.sanitize_input([1, 2, 3]) == ""
        assert validator.sanitize_input({'key': 'value'}) == ""
