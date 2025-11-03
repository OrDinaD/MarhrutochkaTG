#!/usr/bin/env python3
"""
Тесты для callback обработчиков бота
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from telegram.ext import ConversationHandler


class TestCallbackTracking:
    """Тесты системы отслеживания callbacks"""
    
    @pytest.mark.asyncio
    async def test_track_callback_start(self):
        """Тест начала отслеживания callback"""
        from bot import track_callback_start, active_callbacks
        
        user_id = 12345
        query_id = "test_query_123"
        handler_name = "test_handler"
        
        await track_callback_start(user_id, query_id, handler_name)
        
        assert user_id in active_callbacks
        assert active_callbacks[user_id]['query_id'] == query_id
        assert active_callbacks[user_id]['handler'] == handler_name
        assert 'start_time' in active_callbacks[user_id]
    
    @pytest.mark.asyncio
    async def test_track_callback_end(self):
        """Тест окончания отслеживания callback"""
        from bot import track_callback_start, track_callback_end, active_callbacks
        
        user_id = 12345
        query_id = "test_query_123"
        handler_name = "test_handler"
        
        await track_callback_start(user_id, query_id, handler_name)
        assert user_id in active_callbacks
        
        await track_callback_end(user_id)
        assert user_id not in active_callbacks
    
    @pytest.mark.asyncio
    async def test_cleanup_stuck_callbacks(self):
        """Тест очистки застрявших callbacks"""
        from bot import cleanup_stuck_callbacks, active_callbacks
        
        # Добавляем старый callback
        old_time = datetime.now() - timedelta(seconds=60)
        active_callbacks[12345] = {
            'query_id': 'old_query',
            'start_time': old_time,
            'handler': 'old_handler'
        }
        
        # Добавляем свежий callback
        active_callbacks[67890] = {
            'query_id': 'fresh_query',
            'start_time': datetime.now(),
            'handler': 'fresh_handler'
        }
        
        await cleanup_stuck_callbacks()
        
        # Старый должен быть удален
        assert 12345 not in active_callbacks
        # Свежий должен остаться
        assert 67890 in active_callbacks
        
        # Очищаем после теста
        active_callbacks.clear()
    
    @pytest.mark.asyncio
    async def test_emergency_conversation_reset(self):
        """Тест экстренного сброса разговора"""
        from bot import emergency_conversation_reset, active_callbacks
        
        user_id = 12345
        
        # Мокаем context
        context = Mock()
        context.user_data = {'some': 'data'}
        
        # Добавляем активный callback
        active_callbacks[user_id] = {
            'query_id': 'test',
            'start_time': datetime.now(),
            'handler': 'test'
        }
        
        await emergency_conversation_reset(user_id, context)
        
        # Проверяем что данные очищены
        assert len(context.user_data) == 0
        assert user_id not in active_callbacks


class TestCallbackHandlerProtection:
    """Тесты защиты callback handlers"""
    
    @pytest.mark.asyncio
    async def test_callback_handler_protection_success(self):
        """Тест успешной обработки с защитой"""
        from bot import callback_handler_protection
        
        # Создаём тестовую функцию
        @callback_handler_protection(timeout=5)
        async def test_handler(update, context):
            return "success"
        
        # Мокаем update и context
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        result = await test_handler(update, context)
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_callback_handler_protection_timeout(self):
        """Тест обработки таймаута"""
        from bot import callback_handler_protection
        import asyncio
        
        # Создаём функцию которая зависает
        @callback_handler_protection(timeout=1)
        async def slow_handler(update, context):
            await asyncio.sleep(10)
            return "never_reached"
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        result = await slow_handler(update, context)
        
        # Должен вернуть END из-за таймаута
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_callback_handler_protection_exception(self):
        """Тест обработки исключений"""
        from bot import callback_handler_protection
        
        # Создаём функцию которая выбрасывает ошибку
        @callback_handler_protection(timeout=5)
        async def error_handler(update, context):
            raise ValueError("Test error")
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        result = await error_handler(update, context)
        
        # Должен вернуть END из-за ошибки
        assert result == ConversationHandler.END


class TestMonitoringScheduler:
    """Тесты планировщика мониторингов"""
    
    @pytest.mark.asyncio
    async def test_restart_monitoring_scheduler_no_queue(self):
        """Тест перезапуска без job_queue"""
        from bot import restart_monitoring_scheduler
        
        with patch('bot.job_queue', None):
            result = await restart_monitoring_scheduler()
            
            assert result['success'] is False
            assert result['reason'] == 'job_queue_unavailable'
    
    @pytest.mark.asyncio
    async def test_restart_monitoring_scheduler_success(self):
        """Тест успешного перезапуска планировщика"""
        from bot import restart_monitoring_scheduler
        
        # Мокаем job_queue
        mock_job_queue = Mock()
        mock_job = Mock()
        mock_job.schedule_removal = Mock()
        mock_job_queue.jobs = Mock(return_value=[mock_job])
        mock_job_queue.run_repeating = Mock()
        
        with patch('bot.job_queue', mock_job_queue), \
             patch('bot.active_monitors', {}):
            result = await restart_monitoring_scheduler()
            
            assert 'jobs_removed' in result
            assert 'monitors_restored' in result
    
    @pytest.mark.asyncio
    async def test_trigger_bot_restart(self):
        """Тест инициации перезапуска бота"""
        from bot import trigger_bot_restart
        
        context = Mock()
        context.application = Mock()
        context.application.bot_data = {}
        context.application.stop_running = Mock()
        
        await trigger_bot_restart(context)
        
        # Проверяем что stop_running был вызван
        context.application.stop_running.assert_called_once()
        
        # Проверяем что установлен флаг перезапуска
        assert 'restart_info' in context.application.bot_data
        assert context.application.bot_data['restart_info']['pending'] is True


class TestUtilityFunctions:
    """Тесты вспомогательных функций"""
    
    def test_create_webapp_url(self):
        """Тест создания URL веб-приложения"""
        from bot import create_webapp_url
        
        url = create_webapp_url('minsk_ostrovets')
        
        assert isinstance(url, str)
        assert len(url) > 0
        assert 'бел' in url or 'xn--' in url
    
    def test_create_webapp_url_with_date(self):
        """Тест создания URL с датой"""
        from bot import create_webapp_url
        
        url = create_webapp_url('minsk_ostrovets', '2025-11-03')
        
        assert isinstance(url, str)
        assert len(url) > 0
    
    def test_create_webapp_keyboard(self):
        """Тест создания клавиатуры с веб-приложением"""
        from bot import create_webapp_keyboard
        
        keyboard = create_webapp_keyboard('minsk_ostrovets')
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
    
    def test_create_webapp_keyboard_both_directions(self):
        """Тест клавиатуры для обоих направлений"""
        from bot import create_webapp_keyboard
        
        keyboard = create_webapp_keyboard('both')
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
    
    def test_format_monitor_config(self):
        """Тест форматирования конфигурации мониторинга"""
        from bot import format_monitor_config
        
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
    
    def test_get_main_menu_keyboard(self):
        """Тест получения главного меню"""
        from bot import get_main_menu_keyboard
        
        # Инициализируем admin_panel
        with patch('bot.admin_panel', None):
            keyboard = get_main_menu_keyboard(12345)
            
            assert keyboard is not None
            assert len(keyboard.inline_keyboard) > 0


class TestLoggingFunctions:
    """Тесты функций логирования"""
    
    def test_safe_log_system(self):
        """Тест системного логирования"""
        from bot import safe_log_system
        
        # Не должно вызывать ошибок
        safe_log_system("Test message")
        safe_log_system("Test with data", {"key": "value"})
        safe_log_system("Test with level", level="warning")
    
    def test_safe_log_bot(self):
        """Тест логирования бота"""
        from bot import safe_log_bot
        
        # Не должно вызывать ошибок
        safe_log_bot("Test message")
        safe_log_bot("Test with data", {"user_id": 12345})
    
    def test_safe_log_admin(self):
        """Тест административного логирования"""
        from bot import safe_log_admin
        
        # Не должно вызывать ошибок
        safe_log_admin("Test message")
        safe_log_admin("Admin action", {"action": "restart"})
    
    def test_safe_log_universal(self):
        """Тест универсальной функции логирования"""
        from bot import safe_log
        
        # Тестируем разные типы логов
        safe_log("System test", "system")
        safe_log("Bot test", "bot")
        safe_log("Admin test", "admin")
        safe_log("Custom test", "custom")


class TestErrorHandler:
    """Тесты обработки ошибок"""
    
    @pytest.mark.asyncio
    async def test_error_handler_with_user(self):
        """Тест обработчика ошибок с пользователем"""
        from bot import error_handler
        
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.effective_chat = Mock()
        update.effective_chat.id = 12345
        update.effective_message = Mock()
        update.effective_message.message_id = 999
        
        context = Mock()
        context.error = ValueError("Test error")
        
        # Не должно вызывать ошибок
        await error_handler(update, context)
    
    @pytest.mark.asyncio
    async def test_error_handler_without_user(self):
        """Тест обработчика ошибок без пользователя"""
        from bot import error_handler
        
        update = Mock()
        update.effective_user = None
        update.effective_chat = None
        update.effective_message = None
        
        context = Mock()
        context.error = RuntimeError("Test runtime error")
        
        # Не должно вызывать ошибок
        await error_handler(update, context)


class TestParserInitialization:
    """Тесты инициализации парсера"""
    
    @pytest.mark.asyncio
    async def test_init_parser(self):
        """Тест инициализации парсера"""
        from bot import init_parser
        
        with patch('bot.FinalMarshrutochkaParser') as MockParser:
            mock_parser = Mock()
            mock_parser.__aenter__ = AsyncMock()
            MockParser.return_value = mock_parser
            
            with patch('bot.parser', None):
                await init_parser()
                
                # Проверяем что парсер был создан
                MockParser.assert_called_once()
