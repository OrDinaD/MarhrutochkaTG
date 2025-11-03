#!/usr/bin/env python3
"""
Тесты для нормализации и валидации диапазонов времени
"""

import pytest

from security import SecurityValidator


class TestTimeValidation:
    """Тесты валидации времени и диапазонов"""

    def validate_time_range(self, text: str):
        """Прокси над SecurityValidator для тестирования"""
        normalized = SecurityValidator.normalize_time_range(text)
        return (normalized is not None), normalized

    @pytest.mark.parametrize(
        "time_range, expected_valid, expected_normalized",
        [
            ("07:00-09:00", True, "07:00-09:00"),
            ("17:30-19:30", True, "17:30-19:30"),
            ("00:00-23:59", True, "00:00-23:59"),
            ("12:00-12:01", True, "12:00-12:01"),
            ("07:00 - 09:00", True, "07:00-09:00"),
            (" 07:00–09:00 ", True, "07:00-09:00"),
            ("22:00-02:00", True, "22:00-02:00"),
            ("7:00-9:00", True, "07:00-09:00"),
            ("07:00-7:30", True, "07:00-07:30"),
            ("23:59-00:30", True, "23:59-00:30"),
            ("10:00-10:00", False, None),
            ("25:00-09:00", False, None),
            ("07:00-25:00", False, None),
            ("07:60-09:00", False, None),
            ("07:00-09:60", False, None),
            ("abc-def", False, None),
            ("", False, None),
            ("07:00", False, None),
            ("07:00-", False, None),
            ("-09:00", False, None),
        ],
    )
    def test_time_range_validation(self, time_range, expected_valid, expected_normalized):
        """Проверяет основные сценарии нормализации диапазонов"""
        is_valid, normalized = self.validate_time_range(time_range)
        assert is_valid == expected_valid, f"{time_range}: ожидалось {expected_valid}, получено {is_valid}"
        assert normalized == expected_normalized

    @pytest.mark.parametrize(
        "time_range",
        [
            "abc:def-ghi:jkl",
            "12-34:56:78",
            "1a:2b-3c:4d",
            "12::34-56::78",
            "07:0a-09:00",
            "07:00-09:0b",
        ],
    )
    def test_time_parsing_error_handling(self, time_range):
        """Проверяет, что некорректные строки отклоняются"""
        is_valid, normalized = self.validate_time_range(time_range)
        assert not is_valid, f"Диапазон {time_range} должен быть невалидным"
        assert normalized is None

    def test_validate_time_range_wrapper(self):
        """Проверяет булевый хелпер"""
        assert SecurityValidator.validate_time_range("07:00-09:00")
        assert SecurityValidator.validate_time_range("22:00-02:00")
        assert not SecurityValidator.validate_time_range("12:00-12:00")
