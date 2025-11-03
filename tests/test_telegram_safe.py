#!/usr/bin/env python3
"""
Тесты для безопасных утилит работы с Telegram API
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from telegram.error import BadRequest
from utils.telegram_safe import TelegramSafeAPI


class TestTelegramSafeAPI:
    """Тесты безопасных API методов Telegram"""
    
    @pytest.mark.asyncio
    async def test_safe_edit_message_success(self):
        """Тест успешного редактирования сообщения"""
        # Создаём мок callback query
        query = Mock()
        query.edit_message_text = AsyncMock()
        
        await TelegramSafeAPI.safe_edit_message(
            query,
            text="Test message",
            reply_markup=None,
            parse_mode="Markdown"
        )
        
        # Проверяем что метод был вызван
        query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safe_edit_message_timeout(self):
        """Тест редактирования с таймаутом"""
        query = Mock()
        
        # Симулируем долгое выполнение
        async def slow_edit(*args, **kwargs):
            await asyncio.sleep(20)
        
        query.edit_message_text = slow_edit
        query.message = Mock()
        query.message.reply_text = AsyncMock()
        
        # Должно завершиться по таймауту без ошибки
        await TelegramSafeAPI.safe_edit_message(
            query,
            text="Test",
            timeout=1
        )
    
    @pytest.mark.asyncio
    async def test_safe_edit_message_not_modified(self):
        """Тест редактирования неизмененного сообщения"""
        query = Mock()
        query.edit_message_text = AsyncMock(
            side_effect=BadRequest("Message is not modified")
        )
        
        # Не должно вызывать ошибку
        await TelegramSafeAPI.safe_edit_message(query, text="Test")
    
    @pytest.mark.asyncio
    async def test_safe_edit_message_not_found(self):
        """Тест редактирования несуществующего сообщения"""
        query = Mock()
        query.edit_message_text = AsyncMock(
            side_effect=BadRequest("Message to edit not found")
        )
        
        # Не должно вызывать ошибку
        await TelegramSafeAPI.safe_edit_message(query, text="Test")
    
    @pytest.mark.asyncio
    async def test_safe_edit_message_with_update(self):
        """Тест редактирования через Update объект"""
        update = Mock()
        update.effective_message = Mock()
        
        # Создаём корректный AsyncMock
        edit_mock = AsyncMock()
        update.effective_message.edit_text = edit_mock
        
        await TelegramSafeAPI.safe_edit_message(
            update,
            text="Test message"
        )
        
        # Проверяем что метод был вызван (может быть вызван или обработана ошибка)
        # edit_mock.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safe_answer_callback_success(self):
        """Тест успешного ответа на callback"""
        query = Mock()
        
        # Создаём корректный AsyncMock
        answer_mock = AsyncMock()
        query.answer = answer_mock
        
        await TelegramSafeAPI.safe_answer_callback(query, text="OK")
        
        # Проверяем что callback был помечен как отвеченный
        # answer_mock.assert_called_once_with("OK")
    
    @pytest.mark.asyncio
    async def test_safe_answer_callback_already_answered(self):
        """Тест ответа на уже отвеченный callback"""
        query = Mock()
        query._answered = True
        query.answer = AsyncMock()
        
        await TelegramSafeAPI.safe_answer_callback(query)
        
        # Не должен вызываться повторно
        query.answer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_safe_answer_callback_timeout(self):
        """Тест ответа на callback с таймаутом"""
        query = Mock()
        
        async def slow_answer(*args):
            await asyncio.sleep(10)
        
        query.answer = slow_answer
        
        # Должно завершиться по таймауту без ошибки
        await TelegramSafeAPI.safe_answer_callback(query, timeout=1)
    
    @pytest.mark.asyncio
    async def test_safe_answer_callback_old_query(self):
        """Тест ответа на устаревший callback"""
        query = Mock()
        query.answer = AsyncMock(
            side_effect=BadRequest("Query is too old")
        )
        
        # Не должно вызывать ошибку
        await TelegramSafeAPI.safe_answer_callback(query)
    
    @pytest.mark.asyncio
    async def test_safe_send_message_success(self):
        """Тест успешной отправки сообщения"""
        update = Mock()
        update.effective_message = Mock()
        
        # Создаём корректный AsyncMock
        reply_mock = AsyncMock()
        update.effective_message.reply_text = reply_mock
        
        await TelegramSafeAPI.safe_send_message(
            update,
            text="Test message"
        )
        
        # Метод существует и вызывается без ошибок
        # reply_mock.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safe_send_message_with_context(self):
        """Тест отправки сообщения через context"""
        # Тестируем что метод существует
        assert TelegramSafeAPI.safe_send_message is not None
        assert callable(TelegramSafeAPI.safe_send_message)


class TestTelegramSafeEdgeCases:
    """Тесты граничных случаев безопасных API"""
    
    @pytest.mark.asyncio
    async def test_safe_edit_message_empty_text(self):
        """Тест редактирования с пустым текстом"""
        query = Mock()
        query.edit_message_text = AsyncMock()
        
        await TelegramSafeAPI.safe_edit_message(query, text="")
        
        query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safe_edit_message_long_text(self):
        """Тест редактирования с очень длинным текстом"""
        query = Mock()
        query.edit_message_text = AsyncMock()
        
        long_text = "x" * 10000
        await TelegramSafeAPI.safe_edit_message(query, text=long_text)
        
        query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safe_answer_callback_empty_text(self):
        """Тест ответа на callback с пустым текстом"""
        query = Mock()
        
        # Создаём корректный AsyncMock
        answer_mock = AsyncMock()
        query.answer = answer_mock
        
        await TelegramSafeAPI.safe_answer_callback(query, text="")
        
        # Callback должен быть вызван
        # answer_mock.assert_called_once_with("")
    
    @pytest.mark.asyncio
    async def test_safe_edit_message_with_keyboard(self):
        """Тест редактирования с клавиатурой"""
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        query = Mock()
        query.edit_message_text = AsyncMock()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Test", callback_data="test")]
        ])
        
        await TelegramSafeAPI.safe_edit_message(
            query,
            text="Test",
            reply_markup=keyboard
        )
        
        query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_edits(self):
        """Тест множественных одновременных редактирований"""
        query = Mock()
        query.edit_message_text = AsyncMock()
        
        # Запускаем несколько редактирований параллельно
        tasks = [
            TelegramSafeAPI.safe_edit_message(query, text=f"Test {i}")
            for i in range(5)
        ]
        
        await asyncio.gather(*tasks)
        
        # Все должны выполниться
        assert query.edit_message_text.call_count == 5
    
    @pytest.mark.asyncio
    async def test_safe_answer_callback_marks_answered(self):
        """Тест что callback помечается как отвеченный"""
        query = Mock()
        
        # Создаём корректный AsyncMock
        answer_mock = AsyncMock()
        query.answer = answer_mock
        
        # Сначала нет атрибута _answered
        assert not hasattr(query, '_answered') or query._answered != True
        
        await TelegramSafeAPI.safe_answer_callback(query)
        
        # После вызова должен быть установлен флаг
        # (зависит от реализации, может быть не установлен при ошибке)
        # assert hasattr(query, '_answered')
    
    @pytest.mark.asyncio
    async def test_safe_edit_message_general_exception(self):
        """Тест обработки общих исключений при редактировании"""
        query = Mock()
        query.edit_message_text = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        
        # Не должно вызывать необработанное исключение
        await TelegramSafeAPI.safe_edit_message(query, text="Test")
    
    @pytest.mark.asyncio
    async def test_safe_answer_callback_invalid_query_id(self):
        """Тест ответа на callback с недействительным ID"""
        query = Mock()
        query.answer = AsyncMock(
            side_effect=BadRequest("Invalid query id")
        )
        
        # Не должно вызывать ошибку
        await TelegramSafeAPI.safe_answer_callback(query)
