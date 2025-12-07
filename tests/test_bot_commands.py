#!/usr/bin/env python3
"""
Тесты для command handlers и основных команд бота
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram.ext import ConversationHandler


class TestCommandHandlers:
    """Тесты обработчиков команд"""
    
    @pytest.mark.asyncio
    async def test_start_command(self):
        """Тест команды /start"""
        from bot import start
        
        update = Mock()
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        
        await start(update, context)
        
        # Проверяем что сообщение было отправлено
        update.message.reply_text.assert_called_once()
        
        # Проверяем текст приветствия
        call_args = update.message.reply_text.call_args
        assert "Добро пожаловать" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_main_menu(self):
        """Тест главного меню"""
        from bot import handle_main_menu
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {'some': 'data'}
        
        result = await handle_main_menu(update, context)
        
        # Должен вернуть END для завершения conversation
        assert result == ConversationHandler.END
        
        # user_data должен быть очищен
        assert len(context.user_data) == 0
    
    @pytest.mark.asyncio
    async def test_cancel_conversation(self):
        """Тест отмены conversation"""
        from bot import cancel_conversation
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        result = await cancel_conversation(update, context)
        
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_my_monitors_active(self):
        """Тест просмотра активного мониторинга"""
        from bot import my_monitors
        
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.callback_query = Mock()
        update.callback_query.edit_message_text = AsyncMock()
        
        context = Mock()
        
        # Добавляем активный мониторинг
        with patch('bot.active_monitors', {
            12345: {
                'date': '2025-11-03',
                'direction': 'minsk_ostrovets',
                'time_type': 'departure',
                'time_range': '08:00-10:00',
                'created_at': '2025-11-03T10:00:00'
            }
        }):
            await my_monitors(update, context)
            
            # Проверяем что сообщение было отправлено
            update.callback_query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_my_monitors_inactive(self):
        """Тест просмотра мониторинга когда он не активен"""
        from bot import my_monitors
        
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.callback_query = None
        
        context = Mock()
        
        with patch('bot.active_monitors', {}):
            await my_monitors(update, context)
            
            # Проверяем что сообщение было отправлено
            update.message.reply_text.assert_called_once()
            
            # Проверяем текст
            call_args = update.message.reply_text.call_args
            assert "не активен" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_stop_monitoring_success(self):
        """Тест успешной остановки мониторинга"""
        from bot import stop_monitoring, active_monitors
        from managers.user_manager import user_manager
        
        # Добавляем активный мониторинг
        active_monitors[12345] = {
            'direction': 'minsk_ostrovets',
            'date': '2024-01-01',
            'job': Mock()
        }
        
        # Сетапим в user_manager тоже
        user_manager.set_user_monitor(12345, active_monitors[12345])
        
        update = Mock()
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.callback_query = None  # Чтобы использовать reply_text
        
        context = Mock()
        
        await stop_monitoring(update, context)
        
        # Проверяем что мониторинг удалён
        assert user_manager.get_user_monitor(12345) is None
        # Проверяем что функция вызвалась
        update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring_not_active(self):
        """Тест остановки несуществующего мониторинга"""
        from bot import stop_monitoring
        
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.callback_query = None
        
        context = Mock()
        
        with patch('bot.user_manager') as mock_manager:
            mock_manager.remove_user_monitor = Mock(return_value=False)
            
            await stop_monitoring(update, context)
            
            # Проверяем что было отправлено сообщение
            update.message.reply_text.assert_called_once()


class TestConversationHandlers:
    """Тесты обработчиков conversation"""
    
    @pytest.mark.asyncio
    async def test_start_monitoring_conversation_from_callback(self):
        """Тест начала настройки мониторинга из callback"""
        from bot import start_monitoring_conversation, CHOOSE_DATE
        
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.callback_query = Mock()
        update.callback_query.edit_message_text = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {}):
            result = await start_monitoring_conversation(update, context)
            
            assert result == CHOOSE_DATE
            update.callback_query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_monitoring_conversation_from_message(self):
        """Тест начала настройки мониторинга из сообщения"""
        from bot import start_monitoring_conversation, CHOOSE_DATE
        
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.callback_query = None
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {}):
            result = await start_monitoring_conversation(update, context)
            
            assert result == CHOOSE_DATE
            update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_date_choice_simple(self):
        """Тест выбора даты"""
        from bot import handle_date_choice, CHOOSE_DIRECTION
        
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
        
        with patch('bot.user_data_store', {12345: {}}):
            result = await handle_date_choice(update, context)
            
            assert result == CHOOSE_DIRECTION
    
    @pytest.mark.asyncio
    async def test_handle_date_choice_custom(self):
        """Тест выбора кастомной даты"""
        from bot import handle_date_choice, CHOOSE_DATE
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "custom_date"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {12345: {}}):
            result = await handle_date_choice(update, context)
            
            assert result == CHOOSE_DATE
    
    @pytest.mark.asyncio
    async def test_handle_date_choice_back_to_main(self):
        """Тест возврата в главное меню из выбора даты"""
        from bot import handle_date_choice
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "back_to_main"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {12345: {'some': 'data'}}):
            result = await handle_date_choice(update, context)
            
            assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_handle_monitoring_direction_choice(self):
        """Тест выбора направления для мониторинга"""
        from bot import handle_monitoring_direction_choice, CHOOSE_TIME_RANGE
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "dir_minsk_ostrovets"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {12345: {'date': '2025-11-03'}}):
            result = await handle_monitoring_direction_choice(update, context)

            assert result == CHOOSE_TIME_RANGE
    
    @pytest.mark.asyncio
    async def test_handle_monitoring_direction_back(self):
        """Тест возврата к выбору даты из направления"""
        from bot import handle_monitoring_direction_choice, CHOOSE_DATE
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "back_to_date"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {12345: {}}):
            result = await handle_monitoring_direction_choice(update, context)
            
            assert result == CHOOSE_DATE
    
    @pytest.mark.asyncio
    async def test_handle_time_type_choice(self):
        """Тест выбора типа времени"""
        from bot import handle_time_type_choice, CHOOSE_TIME_RANGE
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.id = "test_query"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "time_departure"
        update.effective_user = Mock()
        update.effective_user.id = 12345
        
        context = Mock()
        context.user_data = {}
        
        with patch('bot.user_data_store', {12345: {
            'date': '2025-11-03',
            'direction': 'minsk_ostrovets'
        }}):
            result = await handle_time_type_choice(update, context)
            
            assert result == CHOOSE_TIME_RANGE


class TestKeyboardFactoryIntegration:
    """Тесты интеграции с фабрикой клавиатур"""
    
    def test_get_date_keyboard(self):
        """Тест получения клавиатуры дат"""
        from bot import get_date_keyboard
        
        keyboard = get_date_keyboard()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
    
    def test_get_direction_keyboard(self):
        """Тест получения клавиатуры направлений"""
        from bot import get_direction_keyboard
        
        keyboard = get_direction_keyboard()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
    
    def test_get_time_type_keyboard(self):
        """Тест получения клавиатуры типов времени"""
        from bot import get_time_type_keyboard
        
        keyboard = get_time_type_keyboard()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
    
    def test_get_time_range_keyboard(self):
        """Тест получения клавиатуры диапазонов времени"""
        from bot import get_time_range_keyboard
        
        keyboard = get_time_range_keyboard('departure')
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
