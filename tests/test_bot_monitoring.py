#!/usr/bin/env python3
"""
Тесты для поиска маршрутов и обработки мониторинга
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram.ext import ConversationHandler


class TestTimeRangeHandler:
    """Тесты обработки выбора диапазона времени"""
    
    @pytest.mark.asyncio
    async def test_handle_time_range_choice_simple(self):
        """Тест выбора простого диапазона"""
        from bot import handle_time_range_choice, CONFIRM_MONITORING
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "range_08:00-10:00"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {12345: {
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure'
        }}):
            result = await handle_time_range_choice(update, context)
            
            assert result == CONFIRM_MONITORING
    
    @pytest.mark.asyncio
    async def test_handle_time_range_choice_custom(self):
        """Тест выбора кастомного диапазона"""
        from bot import handle_time_range_choice, CHOOSE_TIME_RANGE
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "range_custom"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {12345: {
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure'
        }}):
            result = await handle_time_range_choice(update, context)
            
            assert result == CHOOSE_TIME_RANGE
    
    @pytest.mark.asyncio
    async def test_handle_time_range_choice_back(self):
        """Тест возврата к списку диапазонов"""
        from bot import handle_time_range_choice, CHOOSE_TIME_RANGE
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "back_to_range_list"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {12345: {
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure'
        }}):
            result = await handle_time_range_choice(update, context)
            
            assert result == CHOOSE_TIME_RANGE


class TestMonitoringHelpers:
    """Тесты вспомогательных функций мониторинга"""
    
    @pytest.mark.asyncio
    async def test_ensure_monitoring_session_valid(self):
        """Тест проверки валидной сессии мониторинга"""
        from bot import _ensure_monitoring_session
        
        user_id = 12345
        query = Mock()
        query.message = Mock()
        query.message.chat_id = 12345
        query.edit_message_text = AsyncMock()
        
        context = Mock()
        
        session_data = {
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '08:00-10:00'
        }
        
        with patch('bot.user_data_store', {12345: session_data}):
            result = await _ensure_monitoring_session(user_id, query, context)
            
            assert result is not None
            assert result['date'] == '2025-11-03'
    
    @pytest.mark.asyncio
    async def test_ensure_monitoring_session_missing(self):
        """Тест проверки отсутствующей сессии"""
        from bot import _ensure_monitoring_session
        
        user_id = 12345
        query = Mock()
        query.edit_message_text = AsyncMock()
        
        context = Mock()
        
        with patch('bot.user_data_store', {}):
            result = await _ensure_monitoring_session(user_id, query, context)
            
            assert result is None
            query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_monitoring_session_incomplete(self):
        """Тест проверки неполной сессии"""
        from bot import _ensure_monitoring_session
        
        user_id = 12345
        query = Mock()
        query.edit_message_text = AsyncMock()
        
        context = Mock()
        
        # Неполные данные (нет time_range)
        session_data = {
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure'
        }
        
        with patch('bot.user_data_store', {12345: session_data}):
            result = await _ensure_monitoring_session(user_id, query, context)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_store_monitoring_config(self):
        """Тест сохранения конфигурации мониторинга"""
        from bot import _store_monitoring_config
        
        user_id = 12345
        query = Mock()
        query.message = Mock()
        query.message.chat_id = 12345
        query.edit_message_text = AsyncMock()
        
        context = Mock()
        
        session = {
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '08:00-10:00'
        }
        
        with patch('bot.user_manager') as mock_manager, \
             patch('bot.job_queue', None):
            
            mock_manager.set_user_monitor = Mock()
            mock_manager.get_user_monitor = Mock(return_value=session)
            
            await _store_monitoring_config(user_id, query, context, session)
            
            # Проверяем что мониторинг был сохранен
            mock_manager.set_user_monitor.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_monitoring_config_with_job_queue(self):
        """Тест сохранения конфигурации с job queue"""
        from bot import _store_monitoring_config
        
        user_id = 12345
        query = Mock()
        query.message = Mock()
        query.message.chat_id = 12345
        query.edit_message_text = AsyncMock()
        
        context = Mock()
        
        session = {
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '08:00-10:00'
        }
        
        mock_job_queue = Mock()
        mock_job_queue.run_repeating = Mock()
        
        with patch('bot.user_manager') as mock_manager, \
             patch('bot.job_queue', mock_job_queue):
            
            mock_manager.set_user_monitor = Mock()
            mock_manager.get_user_monitor = Mock(return_value=session)
            
            await _store_monitoring_config(user_id, query, context, session)
            
            # Проверяем что задача была добавлена
            mock_job_queue.run_repeating.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_show_adjust_menu_with_session(self):
        """Тест показа меню изменения параметров"""
        from bot import _show_adjust_menu
        
        user_id = 12345
        query = Mock()
        query.edit_message_text = AsyncMock()
        
        with patch('bot.user_data_store', {12345: {'date': '2025-11-03'}}):
            await _show_adjust_menu(user_id, query)
            
            query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_show_adjust_menu_without_session(self):
        """Тест показа меню без активной сессии"""
        from bot import _show_adjust_menu
        
        user_id = 12345
        query = Mock()
        query.edit_message_text = AsyncMock()
        
        with patch('bot.user_data_store', {}):
            result = await _show_adjust_menu(user_id, query)
            
            assert result == ConversationHandler.END
            query.edit_message_text.assert_called_once()


class TestConversationStates:
    """Тесты состояний conversation"""
    
    def test_conversation_states_defined(self):
        """Тест что все состояния определены"""
        from bot import (
            CHOOSE_DATE, CHOOSE_DIRECTION, CHOOSE_TIME_TYPE,
            CHOOSE_TIME_RANGE, CONFIRM_MONITORING, SEARCH_DATE
        )
        
        # Проверяем что все состояния уникальны
        states = [
            CHOOSE_DATE, CHOOSE_DIRECTION, CHOOSE_TIME_TYPE,
            CHOOSE_TIME_RANGE, CONFIRM_MONITORING, SEARCH_DATE
        ]
        
        assert len(states) == len(set(states))
        
        # Проверяем что все состояния это числа
        for state in states:
            assert isinstance(state, int)


class TestGlobalVariables:
    """Тесты глобальных переменных бота"""
    
    def test_active_monitors_initialized(self):
        """Тест инициализации active_monitors"""
        from bot import active_monitors
        
        assert active_monitors is not None
        assert isinstance(active_monitors, dict)
    
    def test_user_data_store_initialized(self):
        """Тест инициализации user_data_store"""
        from bot import user_data_store
        
        assert user_data_store is not None
        assert isinstance(user_data_store, dict)
    
    def test_active_callbacks_initialized(self):
        """Тест инициализации active_callbacks"""
        from bot import active_callbacks
        
        assert active_callbacks is not None
        assert isinstance(active_callbacks, dict)
    
    def test_callback_timeout_defined(self):
        """Тест определения таймаута callback"""
        from bot import callback_timeout_seconds
        
        assert isinstance(callback_timeout_seconds, int)
        assert callback_timeout_seconds > 0
    
    def test_cleanup_job_name_defined(self):
        """Тест определения имени задачи очистки"""
        from bot import CLEANUP_JOB_NAME
        
        assert isinstance(CLEANUP_JOB_NAME, str)
        assert len(CLEANUP_JOB_NAME) > 0


class TestDataDirectory:
    """Тесты работы с директорией данных"""
    
    def test_data_dir_exists(self):
        """Тест существования директории данных"""
        import os
        from bot import DATA_DIR
        
        # Директория должна быть создана при импорте модуля
        assert os.path.exists(DATA_DIR)
        assert os.path.isdir(DATA_DIR)
