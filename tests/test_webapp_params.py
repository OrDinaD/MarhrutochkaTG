#!/usr/bin/env python3
"""
Тесты для проверки передачи параметров через WebApp URL
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bot import create_webapp_url
from src.utils.keyboards import create_webapp_url_helper


class TestWebAppURLParams:
    """Тесты генерации URL с параметрами"""
    
    def test_url_with_direction_and_date(self):
        """Тест URL с направлением и датой"""
        url = create_webapp_url("minsk_ostrovets", "2025-11-25")
        
        assert "билет.маршруточка.бел" in url
        assert "#from=minsk&to=ostrovets&date=2025-11-25" in url
        
    def test_url_with_direction_only(self):
        """Тест URL только с направлением"""
        url = create_webapp_url("ostrovets_minsk")
        
        assert "билет.маршруточка.бел" in url
        assert "#from=ostrovets&to=minsk" in url
        assert "date" not in url
        
    def test_url_with_date_only_ignored(self):
        """Тест что дата без направления не добавляется"""
        url = create_webapp_url(date="2025-11-25")
        
        assert url == "https://билет.маршруточка.бел/"
        assert "#" not in url
        
    def test_url_without_params(self):
        """Тест URL без параметров"""
        url = create_webapp_url()
        
        assert url == "https://билет.маршруточка.бел/"
        assert "#" not in url
        
    def test_url_with_general_direction(self):
        """Тест что 'general' не добавляет параметры"""
        url = create_webapp_url("general", "2025-11-25")
        
        assert url == "https://билет.маршруточка.бел/"
        assert "#" not in url
        
    def test_all_directions(self):
        """Тест всех поддерживаемых направлений"""
        test_cases = [
            ("minsk_ostrovets", "from=minsk&to=ostrovets"),
            ("ostrovets_minsk", "from=ostrovets&to=minsk"),
            ("minsk_smorgon", "from=minsk&to=smorgon"),
            ("smorgon_minsk", "from=smorgon&to=minsk"),
            ("ostrovets_smorgon", "from=ostrovets&to=smorgon"),
            ("smorgon_ostrovets", "from=smorgon&to=ostrovets"),
        ]
        
        for direction, expected_params in test_cases:
            url = create_webapp_url(direction)
            assert f"#{expected_params}" in url, f"Failed for direction: {direction}"
            
    def test_url_helper_function(self):
        """Тест вспомогательной функции из keyboards"""
        url = create_webapp_url_helper("minsk_ostrovets", "2025-11-25")
        
        assert "билет.маршруточка.бел" in url
        assert "#from=minsk&to=ostrovets&date=2025-11-25" in url


class TestWebAppURLFormat:
    """Тесты формата URL"""
    
    def test_hash_format(self):
        """Тест что параметры идут в hash (после #)"""
        url = create_webapp_url("minsk_ostrovets", "2025-11-25")
        
        # Проверяем что есть #
        assert "#" in url
        
        # Проверяем что параметры после #
        hash_index = url.index("#")
        params_part = url[hash_index:]
        
        assert "from=" in params_part
        assert "to=" in params_part
        assert "date=" in params_part
        
    def test_params_separator(self):
        """Тест что параметры разделены &"""
        url = create_webapp_url("minsk_ostrovets", "2025-11-25")
        
        # Извлекаем hash часть
        hash_part = url.split("#")[1]
        
        # Проверяем что параметры разделены &
        assert "&" in hash_part
        assert hash_part.count("&") == 2  # from&to&date
        
    def test_date_format(self):
        """Тест формата даты"""
        url = create_webapp_url("minsk_ostrovets", "2025-11-25")
        
        assert "date=2025-11-25" in url
        
    def test_no_trailing_separator(self):
        """Тест что нет лишних разделителей"""
        url = create_webapp_url("minsk_ostrovets", "2025-11-25")
        
        # Не должно быть двойных &&
        assert "&&" not in url
        
        # Не должно заканчиваться на &
        assert not url.endswith("&")


class TestWebAppURLEdgeCases:
    """Тесты граничных случаев"""
    
    def test_both_direction_no_params(self):
        """Тест что 'both' не добавляет параметры"""
        url = create_webapp_url("both")
        
        assert url == "https://билет.маршруточка.бел/"
        assert "#" not in url
        
    def test_all_direction_no_params(self):
        """Тест что 'all' не добавляет параметры"""
        url = create_webapp_url("all")
        
        assert url == "https://билет.маршруточка.бел/"
        assert "#" not in url
        
    def test_invalid_direction_ignored(self):
        """Тест что неизвестное направление игнорируется"""
        url = create_webapp_url("invalid_direction", "2025-11-25")
        
        assert url == "https://билет.маршруточка.бел/"
        assert "#" not in url
        
    def test_empty_date_ignored(self):
        """Тест что пустая дата игнорируется"""
        url = create_webapp_url("minsk_ostrovets", "")
        
        # Должно быть только направление
        assert "#from=minsk&to=ostrovets" in url
        assert "date=" not in url
        
    def test_none_date_ignored(self):
        """Тест что None дата игнорируется"""
        url = create_webapp_url("minsk_ostrovets", None)
        
        assert "#from=minsk&to=ostrovets" in url
        assert "date=" not in url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
