#!/usr/bin/env python3
"""
Тесты для новой логики динамического расчета времени поездки от Сморгони до Островца
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils.route_analyzer import RouteAnalyzer, generate_static_minsk_smorgon_ostrovets_schedule


class TestDynamicRouteCalculation:
    """Тесты для динамического расчета времени маршрутов"""

    def test_calculate_smorgon_ostrovets_duration_basic(self):
        """Тест базового расчета времени от Сморгони до Островца"""
        # Тестовый маршрут 3ч 15мин через Сморгонь
        test_route = {
            'from_city': 'Минск',
            'to_city': 'Островец',
            'departure_time': '07:00',
            'arrival_time': '10:15',
            'duration': '3 ч 15 мин',
            'via_smorgon': True
        }
        
        result = RouteAnalyzer.calculate_smorgon_ostrovets_duration(test_route)
        
        # Ожидаем: 195 мин (общее) - 125 мин (Минск-Сморгонь) = 70 мин
        assert result == 70
        
    def test_calculate_smorgon_ostrovets_duration_edge_cases(self):
        """Тест граничных случаев для расчета времени"""
        
        # Случай 1: Очень быстрый маршрут (3ч 0мин)
        fast_route = {
            'duration': '3 ч 0 мин',
            'via_smorgon': True
        }
        result = RouteAnalyzer.calculate_smorgon_ostrovets_duration(fast_route)
        assert result == 55  # 180 - 125 = 55
        
        # Случай 2: Медленный маршрут (3ч 30мин)
        slow_route = {
            'duration': '3 ч 30 мин',
            'via_smorgon': True
        }
        result = RouteAnalyzer.calculate_smorgon_ostrovets_duration(slow_route)
        assert result == 85  # 210 - 125 = 85
        
        # Случай 3: Маршрут НЕ через Сморгонь
        non_smorgon_route = {
            'duration': '2 ч 30 мин',
            'via_smorgon': False
        }
        result = RouteAnalyzer.calculate_smorgon_ostrovets_duration(non_smorgon_route)
        assert result is None
        
        # Случай 4: Некорректное время (слишком короткое)
        invalid_route = {
            'duration': '1 ч 30 мин',
            'via_smorgon': True
        }
        result = RouteAnalyzer.calculate_smorgon_ostrovets_duration(invalid_route)
        # Должно вернуть стандартное значение
        assert result == 65

    def test_calculate_minsk_smorgon_duration(self):
        """Тест расчета времени от Минска до Сморгони"""
        test_route = {
            'duration': '3 ч 15 мин',
            'via_smorgon': True
        }
        
        result = RouteAnalyzer.calculate_minsk_smorgon_duration(test_route)
        
        # Ожидаем: 195 мин (общее) - 65 мин (Сморгонь-Островец) = 130 мин
        assert result == 130

    def test_get_average_durations(self):
        """Тест расчета средних времен на основе нескольких маршрутов"""
        test_routes = [
            {'duration': '3 ч 0 мин', 'via_smorgon': True},   # 180 мин
            {'duration': '3 ч 15 мин', 'via_smorgon': True},  # 195 мин
            {'duration': '3 ч 30 мин', 'via_smorgon': True},  # 210 мин
            {'duration': '2 ч 30 мин', 'via_smorgon': False}, # Не должен учитываться
        ]
        
        # Тест среднего времени Сморгонь-Островец
        avg_smorgon_ostrovets = RouteAnalyzer.get_average_smorgon_ostrovets_duration(test_routes)
        # Ожидаем: (55 + 70 + 85) / 3 = 70 (округлено до 5 мин)
        assert avg_smorgon_ostrovets == 70
        
        # Тест среднего времени Минск-Сморгонь
        avg_minsk_smorgon = RouteAnalyzer.get_average_minsk_smorgon_duration(test_routes)
        # Ожидаем: (115 + 130 + 145) / 3 = 130 (округлено до 5 мин)
        assert avg_minsk_smorgon == 130

    def test_parse_duration_various_formats(self):
        """Тест парсинга различных форматов времени"""
        test_cases = [
            ('3 ч 15 мин', 195),
            ('2 ч 30 мин', 150),
            ('1 ч 0 мин', 60),
            ('45 мин', 45),
            ('3ч 15мин', 195),  # Без пробелов
            ('2час 30мин', 150),  # Альтернативный формат
            ('некорректный формат', None),
            ('', None),
            (None, None),
        ]
        
        for duration_str, expected in test_cases:
            result = RouteAnalyzer._parse_duration(duration_str)
            assert result == expected, f"Для '{duration_str}' ожидали {expected}, получили {result}"

    def test_static_schedule_generation_with_real_data(self):
        """Тест генерации статического расписания с учетом реальных данных"""
        # Тестовые данные маршрутов
        real_routes = [
            {'duration': '3 ч 0 мин', 'via_smorgon': True},
            {'duration': '3 ч 15 мин', 'via_smorgon': True},
            {'duration': '3 ч 30 мин', 'via_smorgon': True},
        ]
        
        today = datetime.now().strftime("%Y-%m-%d")
        static_routes = generate_static_minsk_smorgon_ostrovets_schedule(today, real_routes)
        
        assert len(static_routes) > 0
        
        # Проверяем первый маршрут
        first_route = static_routes[0]
        assert 'calculated_minsk_smorgon_minutes' in first_route
        assert 'calculated_smorgon_ostrovets_minutes' in first_route
        assert first_route['via_smorgon'] is True
        assert first_route['from_city'] == 'Минск'
        assert first_route['to_city'] == 'Островец'
        
        # Проверяем что времена разумные
        minsk_smorgon_time = first_route['calculated_minsk_smorgon_minutes']
        smorgon_ostrovets_time = first_route['calculated_smorgon_ostrovets_minutes']
        
        assert 90 <= minsk_smorgon_time <= 150  # Разумное время для Минск-Сморгонь
        assert 30 <= smorgon_ostrovets_time <= 90  # Разумное время для Сморгонь-Островец

    def test_static_schedule_generation_without_real_data(self):
        """Тест генерации статического расписания без реальных данных (fallback)"""
        today = datetime.now().strftime("%Y-%m-%d")
        static_routes = generate_static_minsk_smorgon_ostrovets_schedule(today, None)
        
        assert len(static_routes) > 0
        
        # Проверяем что используются стандартные значения
        first_route = static_routes[0]
        assert first_route['calculated_minsk_smorgon_minutes'] == 125  # Стандартное значение
        assert first_route['calculated_smorgon_ostrovets_minutes'] == 65  # Стандартное значение

    def test_edge_case_empty_routes_list(self):
        """Тест случая с пустым списком маршрутов"""
        empty_routes = []
        
        avg_smorgon_ostrovets = RouteAnalyzer.get_average_smorgon_ostrovets_duration(empty_routes)
        avg_minsk_smorgon = RouteAnalyzer.get_average_minsk_smorgon_duration(empty_routes)
        
        # Должны вернуться стандартные значения
        assert avg_smorgon_ostrovets == 65
        assert avg_minsk_smorgon == 125

    def test_edge_case_only_non_smorgon_routes(self):
        """Тест случая когда все маршруты НЕ через Сморгонь"""
        non_smorgon_routes = [
            {'duration': '2 ч 30 мин', 'via_smorgon': False},
            {'duration': '2 ч 45 мин', 'via_smorgon': False},
        ]
        
        avg_smorgon_ostrovets = RouteAnalyzer.get_average_smorgon_ostrovets_duration(non_smorgon_routes)
        avg_minsk_smorgon = RouteAnalyzer.get_average_minsk_smorgon_duration(non_smorgon_routes)
        
        # Должны вернуться стандартные значения
        assert avg_smorgon_ostrovets == 65
        assert avg_minsk_smorgon == 125

    def test_realistic_scenario(self):
        """Тест реалистичного сценария с смешанными данными"""
        realistic_routes = [
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': '07:00',
                'arrival_time': '10:10',
                'duration': '3 ч 10 мин',
                'via_smorgon': True,
                'route_id': 'morning_1'
            },
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': '09:30',
                'arrival_time': '12:45',
                'duration': '3 ч 15 мин',
                'via_smorgon': True,
                'route_id': 'morning_2'
            },
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': '14:00',
                'arrival_time': '17:25',
                'duration': '3 ч 25 мин',
                'via_smorgon': True,
                'route_id': 'afternoon_1'
            },
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': '16:00',
                'arrival_time': '18:30',
                'duration': '2 ч 30 мин',
                'via_smorgon': False,  # НЕ через Сморгонь
                'route_id': 'direct_route'
            }
        ]
        
        # Проверяем расчеты для отдельных маршрутов
        for route in realistic_routes:
            if route['via_smorgon']:
                smorgon_time = RouteAnalyzer.calculate_smorgon_ostrovets_duration(route)
                minsk_time = RouteAnalyzer.calculate_minsk_smorgon_duration(route)
                
                assert smorgon_time is not None
                assert minsk_time is not None
                assert 30 <= smorgon_time <= 90
                assert 90 <= minsk_time <= 150
            else:
                smorgon_time = RouteAnalyzer.calculate_smorgon_ostrovets_duration(route)
                assert smorgon_time is None
        
        # Проверяем средние значения
        avg_smorgon_ostrovets = RouteAnalyzer.get_average_smorgon_ostrovets_duration(realistic_routes)
        avg_minsk_smorgon = RouteAnalyzer.get_average_minsk_smorgon_duration(realistic_routes)
        
        # Должны быть разумными средними от 3 маршрутов через Сморгонь
        assert 50 <= avg_smorgon_ostrovets <= 80
        assert 110 <= avg_minsk_smorgon <= 140

    def test_time_calculation_consistency(self):
        """Тест консистентности расчетов времени"""
        test_route = {
            'duration': '3 ч 20 мин',  # 200 минут
            'via_smorgon': True
        }
        
        smorgon_ostrovets_time = RouteAnalyzer.calculate_smorgon_ostrovets_duration(test_route)
        minsk_smorgon_time = RouteAnalyzer.calculate_minsk_smorgon_duration(test_route)
        
        # Проверяем что сумма времен близка к общему времени
        total_calculated = smorgon_ostrovets_time + minsk_smorgon_time
        expected_total = 200
        
        # Может быть небольшое расхождение из-за использования стандартных значений
        assert abs(total_calculated - expected_total) <= 10


if __name__ == "__main__":
    # Запуск тестов напрямую
    pytest.main([__file__, "-v", "--tb=short"])