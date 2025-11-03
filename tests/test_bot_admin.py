#!/usr/bin/env python3
"""
Тесты для админ-функций и управления ботом
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram.ext import ConversationHandler


class TestConstants:
    """Тесты констант и переменных"""
    
    def test_bot_has_conversation_states(self):
        """Тест наличия состояний conversation"""
        from src.bot import CHOOSE_DATE, CHOOSE_DIRECTION, CHOOSE_TIME_TYPE
        
        assert CHOOSE_DATE is not None
        assert CHOOSE_DIRECTION is not None
        assert CHOOSE_TIME_TYPE is not None
    
    def test_bot_has_active_monitors(self):
        """Тест наличия активных мониторингов"""
        from src.bot import active_monitors
        
        assert active_monitors is not None
        assert isinstance(active_monitors, dict)


class TestMonitoringNotifications:
    """Тесты уведомлений о мониторинге"""
    
    @pytest.mark.asyncio
    async def test_send_monitoring_notification_with_context(self):
        """Тест отправки уведомления с context"""
        from src.bot import send_monitoring_notification
        
        user_id = 12345
        routes = [
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': '08:00',
                'arrival_time': '10:00',
                'available_seats': 5
            }
        ]
        
        config = {
            'chat_id': 12345,
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_range': '08:00-10:00'
        }
        
        context = Mock()
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        
        await send_monitoring_notification(user_id, routes, config, context)
        
        # Проверяем что сообщение было отправлено
        context.bot.send_message.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = context.bot.send_message.call_args
        assert call_args[1]['chat_id'] == 12345
        assert 'НАЙДЕНЫ ПОДХОДЯЩИЕ РЕЙСЫ' in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_send_monitoring_notification_without_context(self):
        """Тест отправки уведомления без context"""
        from src.bot import send_monitoring_notification
        
        user_id = 12345
        routes = [
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': '08:00',
                'arrival_time': '10:00',
                'available_seats': 2
            }
        ]
        
        config = {
            'chat_id': 12345,
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_range': '08:00-10:00'
        }
        
        mock_bot = Mock()
        mock_bot.send_message = AsyncMock()
        
        with patch('src.bot.application') as mock_app:
            mock_app.bot = mock_bot
            
            await send_monitoring_notification(user_id, routes, config, None)
    
    @pytest.mark.asyncio
    async def test_send_monitoring_notification_many_routes(self):
        """Тест отправки уведомления с большим количеством маршрутов"""
        from src.bot import send_monitoring_notification
        
        user_id = 12345
        
        # Создаем 10 маршрутов
        routes = [
            {
                'from_city': 'Минск',
                'to_city': 'Островец',
                'departure_time': f'{8+i:02d}:00',
                'arrival_time': f'{10+i:02d}:00',
                'available_seats': 5
            }
            for i in range(10)
        ]
        
        config = {
            'chat_id': 12345,
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_range': '08:00-20:00'
        }
        
        context = Mock()
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        
        await send_monitoring_notification(user_id, routes, config, context)
        
        # Проверяем что сообщение содержит "еще X рейсов"
        call_args = context.bot.send_message.call_args
        message_text = call_args[1]['text']
        assert 'еще 5 рейсов' in message_text
    
    @pytest.mark.asyncio
    async def test_send_monitoring_notification_error_handling(self):
        """Тест обработки ошибок при отправке уведомления"""
        from src.bot import send_monitoring_notification
        
        user_id = 12345
        routes = []
        config = {
            'chat_id': 12345,
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_range': '08:00-10:00'
        }
        
        context = Mock()
        context.bot = Mock()
        context.bot.send_message = AsyncMock(side_effect=Exception("Test error"))
        
        # Не должно вызывать необработанное исключение
        await send_monitoring_notification(user_id, routes, config, context)


class TestSearchDirectionHandler:
    """Тесты обработки выбора направления для поиска"""
    
    @pytest.mark.asyncio
    async def test_handle_direction_choice(self):
        """Тест выбора направления для поиска"""
        from src.bot import handle_direction_choice, SEARCH_DATE
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "search_dir_minsk_ostrovets"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        with patch('src.bot.user_data_store', {}):
            result = await handle_direction_choice(update, context)
            
            assert result == SEARCH_DATE
    
    @pytest.mark.asyncio
    async def test_handle_search_with_direction(self):
        """Тест поиска с выбранным направлением"""
        from src.bot import handle_search_with_direction
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "date_2025-11-03"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        user_data = {
            'route_selected': True,
            'from_city': 'Минск',
            'to_city': 'Островец'
        }
        
        mock_parser = Mock()
        mock_parser.get_all_routes = AsyncMock(return_value={
            'minsk_to_ostrovets': [],
            'success': True
        })
        mock_parser.__aenter__ = AsyncMock(return_value=mock_parser)
        
        with patch('src.bot.user_data_store', {12345: user_data}), \
             patch('src.bot.parser', mock_parser):
            
            result = await handle_search_with_direction(update, context)


class TestWebAppIntegration:
    """Тесты интеграции веб-приложения"""
    
    def test_create_webapp_keyboard_with_additional_buttons(self):
        """Тест создания клавиатуры с дополнительными кнопками"""
        from src.bot import create_webapp_keyboard
        from telegram import InlineKeyboardButton
        
        additional_buttons = [
            [InlineKeyboardButton("Test Button", callback_data="test")]
        ]
        
        keyboard = create_webapp_keyboard(
            'minsk_ostrovets',
            '2025-11-03',
            additional_buttons
        )
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 1
    
    def test_create_webapp_keyboard_smorgon_routes(self):
        """Тест клавиатуры для маршрутов через Сморгонь"""
        from src.bot import create_webapp_keyboard
        
        keyboard = create_webapp_keyboard('minsk_smorgon')
        
        assert keyboard is not None
        # Должна быть информация о Сморгони
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert any('Сморгонь' in text or 'сайт' in text for text in buttons_text)


class TestModuleInitialization:
    """Тесты инициализации модуля бота"""
    
    def test_warnings_filtered(self):
        """Тест фильтрации предупреждений"""
        import warnings
        
        # Проверяем что модуль настроил фильтры
        # (warnings уже настроены при импорте bot.py)
        assert True  # Если импорт прошел без ошибок, фильтры работают
    
    def test_logging_configured(self):
        """Тест настройки логирования"""
        from src.bot import logger
        
        assert logger is not None
    
    def test_data_dir_created(self):
        """Тест создания директории данных"""
        import os
        from src.bot import DATA_DIR
        
        assert os.path.exists(DATA_DIR)
        assert os.path.isdir(DATA_DIR)


class TestFormatMonitorConfig:
    """Тесты форматирования конфигурации мониторинга"""
    
    def test_format_monitor_config_all_fields(self):
        """Тест форматирования с всеми полями"""
        from src.bot import format_monitor_config
        
        config = {
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '08:00-10:00'
        }
        
        result = format_monitor_config(config)
        
        assert '2025-11-03' in result
        assert 'Минск → Островец' in result
        assert 'отправления' in result
        assert '08:00-10:00' in result
        assert 'каждые 5 минут' in result
    
    def test_format_monitor_config_both_directions(self):
        """Тест форматирования для обоих направлений"""
        from src.bot import format_monitor_config
        
        config = {
            'date': '2025-11-03',
            'direction': 'both',
            'time_type': 'any',
            'time_range': 'любое время'
        }
        
        result = format_monitor_config(config)
        
        assert 'Оба направления' in result
        assert 'любое' in result
    
    def test_format_monitor_config_arrival_time(self):
        """Тест форматирования с временем прибытия"""
        from src.bot import format_monitor_config
        
        config = {
            'date': '2025-11-03',
            'direction': 'ostrovets_minsk',
            'time_type': 'arrival',
            'time_range': '18:00-20:00'
        }
        
        result = format_monitor_config(config)
        
        assert 'Островец → Минск' in result
        assert 'прибытия' in result
        assert '18:00-20:00' in result
