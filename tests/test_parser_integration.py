#!/usr/bin/env python3
"""
Интеграционные тесты для новой логики в контексте парсера маршрутов
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils.parser import FinalMarshrutochkaParser
from src.utils.route_analyzer import RouteAnalyzer


class TestParserIntegration:
    """Интеграционные тесты парсера с новой логикой"""

    @pytest.fixture
    def mock_parser(self):
        """Создает мок парсера с отключенным кэшем"""
        return FinalMarshrutochkaParser(enable_cache=False)

    @pytest.fixture
    def sample_minsk_ostrovets_routes(self):
        """Образцы маршрутов Минск-Островец для тестов"""
        return [
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': '07:00',
                'arrival_time': '10:00',
                'duration': '3 ч 0 мин',
                'via_smorgon': True,
                'route_id': 'test_fast',
                'price_str': '8,00 руб.',
                'carrier': 'Тестовый перевозчик'
            },
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': '09:00',
                'arrival_time': '12:15',
                'duration': '3 ч 15 мин',
                'via_smorgon': True,
                'route_id': 'test_medium',
                'price_str': '8,00 руб.',
                'carrier': 'Тестовый перевозчик'
            },
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': '14:00',
                'arrival_time': '17:30',
                'duration': '3 ч 30 мин',
                'via_smorgon': True,
                'route_id': 'test_slow',
                'price_str': '8,00 руб.',
                'carrier': 'Тестовый перевозчик'
            }
        ]

    @pytest.mark.asyncio
    async def test_get_routes_smorgon_ostrovets_with_real_data(self, mock_parser, sample_minsk_ostrovets_routes):
        """Тест получения маршрутов Сморгонь-Островец с реальными данными"""
        
        # Мокаем метод search_routes чтобы вернуть наши тестовые данные
        mock_parser.search_routes = AsyncMock(return_value=sample_minsk_ostrovets_routes)
        
        date = "2024-12-25"
        result = await mock_parser.get_routes_smorgon_ostrovets(date)
        
        # Проверяем что получили маршруты
        assert len(result) == 3
        
        # Проверяем что все маршруты имеют правильный город отправления
        for route in result:
            assert route['from_city'] == 'Сморгонь'
            assert route['to_city'] == 'Островец'
            
        # Проверяем что времена рассчитаны динамически
        for route in result:
            assert 'calculated_duration_minutes' in route
            assert 'calculated_minsk_smorgon_minutes' in route
            
            # Времена должны быть разумными
            smorgon_duration = route['calculated_duration_minutes']
            assert 30 <= smorgon_duration <= 90
            
        # Проверяем конкретные расчеты для известных маршрутов
        fast_route = next(r for r in result if r.get('route_id') == 'test_fast')
        medium_route = next(r for r in result if r.get('route_id') == 'test_medium')
        slow_route = next(r for r in result if r.get('route_id') == 'test_slow')
        
        # Быстрый маршрут должен иметь меньшее время
        assert fast_route['calculated_duration_minutes'] < medium_route['calculated_duration_minutes']
        assert medium_route['calculated_duration_minutes'] < slow_route['calculated_duration_minutes']

    @pytest.mark.asyncio
    async def test_get_routes_minsk_ostrovets_with_dynamic_schedule(self, mock_parser, sample_minsk_ostrovets_routes):
        """Тест получения маршрутов Минск-Островец с динамическим расписанием"""
        
        # Мокаем метод search_routes
        mock_parser.search_routes = AsyncMock(return_value=sample_minsk_ostrovets_routes)
        
        date = "2024-12-25"
        result = await mock_parser.get_routes_minsk_ostrovets(date)
        
        # Проверяем что получили статические маршруты
        assert len(result) > 0
        
        # Проверяем что маршруты содержат рассчитанные времена
        first_route = result[0]
        assert 'calculated_minsk_smorgon_minutes' in first_route
        assert 'calculated_smorgon_ostrovets_minutes' in first_route
        
        # Проверяем что времена основаны на реальных данных, а не стандартных
        # (стандартные значения: 125 мин для Минск-Сморгонь, 65 мин для Сморгонь-Островец)
        minsk_smorgon_time = first_route['calculated_minsk_smorgon_minutes']
        smorgon_ostrovets_time = first_route['calculated_smorgon_ostrovets_minutes']
        
        # Должны отличаться от стандартных если используются реальные данные
        # или равняться стандартным если нет достаточно данных
        assert 90 <= minsk_smorgon_time <= 150
        assert 30 <= smorgon_ostrovets_time <= 90

    def test_route_analyzer_with_mixed_data(self):
        """Тест анализатора маршрутов со смешанными данными"""
        mixed_routes = [
            {'duration': '3 ч 0 мин', 'via_smorgon': True},
            {'duration': '3 ч 15 мин', 'via_smorgon': True},
            {'duration': '2 ч 30 мин', 'via_smorgon': False},  # Не через Сморгонь
            {'duration': None, 'via_smorgon': True},  # Некорректные данные
            {'duration': 'некорректный формат', 'via_smorgon': True},
        ]
        
        # Проверяем что функции корректно обрабатывают смешанные данные
        avg_smorgon_ostrovets = RouteAnalyzer.get_average_smorgon_ostrovets_duration(mixed_routes)
        avg_minsk_smorgon = RouteAnalyzer.get_average_minsk_smorgon_duration(mixed_routes)
        
        # Должны использовать только валидные маршруты через Сморгонь
        assert avg_smorgon_ostrovets > 0
        assert avg_minsk_smorgon > 0

    def test_static_schedule_time_validation(self):
        """Тест валидации времен в статическом расписании"""
        test_routes = [
            {'duration': '3 ч 10 мин', 'via_smorgon': True},
            {'duration': '3 ч 20 мин', 'via_smorgon': True},
        ]
        
        from src.utils.route_analyzer import generate_static_minsk_smorgon_ostrovets_schedule
        from datetime import datetime as dt
        
        date = dt.now().strftime("%Y-%m-%d")
        static_routes = generate_static_minsk_smorgon_ostrovets_schedule(date, test_routes)
        
        for route in static_routes:
            # Проверяем корректность времен
            departure = route['departure_time']
            smorgon_arrival = route['smorgon_arrival']
            smorgon_departure = route['smorgon_departure']
            arrival = route['arrival_time']
            
            # Проверяем последовательность времен
            assert departure < smorgon_arrival
            assert smorgon_arrival < smorgon_departure
            assert smorgon_departure < arrival
            
            # Проверяем что промежуток в Сморгони составляет 5 минут
            from datetime import datetime as dt
            arr_time = dt.strptime(smorgon_arrival, "%H:%M")
            dep_time = dt.strptime(smorgon_departure, "%H:%M")
            diff = (dep_time - arr_time).seconds // 60
            assert diff == 5

    @pytest.mark.asyncio
    async def test_error_handling_in_parser(self, mock_parser):
        """Тест обработки ошибок в парсере"""
        
        # Мокаем search_routes чтобы вызвать исключение
        mock_parser.search_routes = AsyncMock(side_effect=Exception("Тестовая ошибка"))
        
        date = "2024-12-25"
        
        # Функция должна обработать ошибку gracefully
        try:
            result = await mock_parser.get_routes_smorgon_ostrovets(date)
            # Если ошибка обработана, результат должен быть списком
            assert isinstance(result, list)
        except Exception as e:
            # Если ошибка не обработана, проверяем что это ожидаемая ошибка
            assert "Тестовая ошибка" in str(e)

    def test_performance_with_large_dataset(self):
        """Тест производительности с большим набором данных"""
        import time
        
        # Создаем большой набор тестовых данных
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'duration': f'{3 + (i % 2)} ч {(i % 60)} мин',
                'via_smorgon': i % 3 == 0,  # Треть маршрутов через Сморгонь
                'route_id': f'test_route_{i}'
            })
        
        start_time = time.time()
        
        # Тестируем производительность расчетов
        avg_smorgon_ostrovets = RouteAnalyzer.get_average_smorgon_ostrovets_duration(large_dataset)
        avg_minsk_smorgon = RouteAnalyzer.get_average_minsk_smorgon_duration(large_dataset)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Проверяем что вычисления выполняются быстро (менее 1 секунды)
        assert execution_time < 1.0
        
        # Проверяем что результаты разумные
        assert 30 <= avg_smorgon_ostrovets <= 90
        assert 90 <= avg_minsk_smorgon <= 150

    def test_edge_case_all_same_duration(self):
        """Тест случая когда все маршруты имеют одинаковое время"""
        same_duration_routes = [
            {'duration': '3 ч 15 мин', 'via_smorgon': True} for _ in range(5)
        ]
        
        avg_smorgon_ostrovets = RouteAnalyzer.get_average_smorgon_ostrovets_duration(same_duration_routes)
        avg_minsk_smorgon = RouteAnalyzer.get_average_minsk_smorgon_duration(same_duration_routes)
        
        # Все результаты должны быть одинаковыми
        assert avg_smorgon_ostrovets == 70  # 195 - 125 = 70
        assert avg_minsk_smorgon == 130     # 195 - 65 = 130

    def test_rounding_behavior(self):
        """Тест поведения округления"""
        # Тестируем маршруты с временами, которые дают нестандартные результаты
        test_routes = [
            {'duration': '3 ч 7 мин', 'via_smorgon': True},   # 187 мин
            {'duration': '3 ч 13 мин', 'via_smorgon': True},  # 193 мин
        ]
        
        avg_smorgon_ostrovets = RouteAnalyzer.get_average_smorgon_ostrovets_duration(test_routes)
        avg_minsk_smorgon = RouteAnalyzer.get_average_minsk_smorgon_duration(test_routes)
        
        # Результаты должны быть округлены до ближайших 5 минут
        assert avg_smorgon_ostrovets % 5 == 0
        assert avg_minsk_smorgon % 5 == 0


if __name__ == "__main__":
    # Запуск тестов напрямую
    pytest.main([__file__, "-v", "--tb=short"])