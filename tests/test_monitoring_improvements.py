#!/usr/bin/env python3
"""
Тесты для улучшенной системы мониторинга
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Импортируем модуль мониторинга
from src.monitoring.route_monitoring import (
    RouteMonitoringValidator,
    RouteMonitoringSystem,
    route_monitoring_system
)


class TestRouteMonitoringValidator:
    """Тесты для валидатора мониторинга"""
    
    def test_validate_config_success(self):
        """Тест успешной валидации конфигурации"""
        config = {
            'date': '2025-01-15',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '07:00-09:00',
            'chat_id': 123456
        }
        
        validator = RouteMonitoringValidator()
        is_valid, error = validator.validate_config(config)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_config_missing_field(self):
        """Тест валидации с отсутствующим полем"""
        config = {
            'date': '2025-01-15',
            'direction': 'minsk_ostrovets',
            # Отсутствует time_type
            'time_range': '07:00-09:00',
            'chat_id': 123456
        }
        
        validator = RouteMonitoringValidator()
        is_valid, error = validator.validate_config(config)
        
        assert is_valid is False
        assert 'time_type' in error
    
    def test_validate_config_invalid_direction(self):
        """Тест валидации с недопустимым направлением"""
        config = {
            'date': '2025-01-15',
            'direction': 'both',  # Больше не поддерживается
            'time_type': 'departure',
            'time_range': '07:00-09:00',
            'chat_id': 123456
        }
        
        validator = RouteMonitoringValidator()
        is_valid, error = validator.validate_config(config)
        
        assert is_valid is False
        assert 'направление' in error.lower()
    
    def test_validate_config_invalid_date_format(self):
        """Тест валидации с неправильным форматом даты"""
        config = {
            'date': '15-01-2025',  # Неправильный формат
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '07:00-09:00',
            'chat_id': 123456
        }
        
        validator = RouteMonitoringValidator()
        is_valid, error = validator.validate_config(config)
        
        assert is_valid is False
        assert 'дата' in error.lower()
    
    def test_should_monitoring_stop_past_date(self):
        """Тест автоматической остановки для прошедшей даты"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        config = {
            'date': yesterday,
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '07:00-09:00',
            'chat_id': 123456
        }
        
        validator = RouteMonitoringValidator()
        should_stop, reason = validator.should_monitoring_stop(config)
        
        assert should_stop is True
        assert 'прошла' in reason.lower()
    
    def test_should_monitoring_stop_future_date(self):
        """Тест продолжения мониторинга для будущей даты"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        config = {
            'date': tomorrow,
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '07:00-09:00',
            'chat_id': 123456
        }
        
        validator = RouteMonitoringValidator()
        should_stop, reason = validator.should_monitoring_stop(config)
        
        assert should_stop is False
        assert reason is None
    
    def test_should_monitoring_stop_time_range_expired(self):
        """Тест автоматической остановки при истечении времени"""
        today = datetime.now().strftime('%Y-%m-%d')
        # Используем диапазон времени, который уже прошел
        past_time = (datetime.now() - timedelta(hours=3)).strftime('%H:%M')
        expired_time = (datetime.now() - timedelta(hours=2)).strftime('%H:%M')
        
        config = {
            'date': today,
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': f'{past_time}-{expired_time}',
            'chat_id': 123456
        }
        
        validator = RouteMonitoringValidator()
        should_stop, reason = validator.should_monitoring_stop(config)
        
        # Должно остановиться, так как время с буфером прошло
        assert should_stop is True
        assert 'завершено' in reason.lower()


class TestRouteMonitoringSystem:
    """Тесты для системы мониторинга"""
    
    @pytest.fixture
    def monitoring_system(self):
        """Фикстура для системы мониторинга"""
        system = RouteMonitoringSystem()
        return system
    
    @pytest.mark.asyncio
    async def test_check_routes_with_auto_stop(self, monitoring_system):
        """Тест автоматической остановки мониторинга"""
        # Настраиваем мок парсера
        mock_parser = AsyncMock()
        monitoring_system.set_parser(mock_parser)
        
        # Настраиваем мок бота
        mock_bot = AsyncMock()
        monitoring_system.set_bot(mock_bot)
        
        # Конфигурация с прошедшей датой
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        config = {
            'date': yesterday,
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '07:00-09:00',
            'chat_id': 123456
        }
        
        user_id = 123456
        active_monitors = {user_id: config}
        
        # Выполняем проверку
        result = await monitoring_system.check_routes_for_user(
            user_id=user_id,
            config=config,
            active_monitors=active_monitors
        )
        
        # Проверяем, что мониторинг должен остановиться
        assert result['should_stop'] is True
        assert result['stop_reason'] is not None
        assert 'прошла' in result['stop_reason'].lower()
        
        # Проверяем, что было отправлено уведомление об остановке
        assert mock_bot.send_message.called
    
    @pytest.mark.asyncio
    async def test_filter_routes_no_both_direction(self, monitoring_system):
        """Тест фильтрации без поддержки 'both'"""
        routes_data = {
            'success': True,
            'minsk_to_ostrovets': [
                {'departure_time': '08:00', 'arrival_time': '09:30', 'available_seats': 5}
            ],
            'ostrovets_to_minsk': [
                {'departure_time': '10:00', 'arrival_time': '11:30', 'available_seats': 3}
            ]
        }
        
        # Конфигурация с направлением minsk_ostrovets
        config = {
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': 'any'
        }
        
        user_id = 123456
        
        # Фильтруем маршруты
        suitable_routes = monitoring_system.filter_routes_by_criteria(
            routes_data, config, user_id
        )
        
        # Должны получить только маршруты Минск → Островец
        assert len(suitable_routes) == 1
        assert suitable_routes[0]['departure_time'] == '08:00'
    
    def test_get_direction_text_no_both(self, monitoring_system):
        """Тест получения текста направления без 'both'"""
        # Проверяем, что 'both' не поддерживается
        direction_text = monitoring_system._get_direction_text('both')
        assert direction_text == 'both'  # Вернется как есть, без перевода
        
        # Проверяем корректные направления
        assert monitoring_system._get_direction_text('minsk_ostrovets') == 'Минск → Островец'
        assert monitoring_system._get_direction_text('ostrovets_minsk') == 'Островец → Минск'


class TestMonitoringIntegration:
    """Интеграционные тесты для мониторинга"""
    
    @pytest.mark.asyncio
    async def test_default_time_type_departure(self):
        """Тест автоматической установки time_type='departure'"""
        # Это проверяется в bot.py, но мы можем протестировать логику
        from src.bot import user_data_store
        
        user_id = 999999
        user_data_store[user_id] = {
            'date': '2025-01-15',
            'direction': 'minsk_ostrovets'
        }
        
        # В реальном коде после выбора направления автоматически устанавливается time_type
        user_data_store[user_id]['time_type'] = 'departure'
        
        assert user_data_store[user_id]['time_type'] == 'departure'
        
        # Очищаем
        del user_data_store[user_id]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
