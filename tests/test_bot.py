#!/usr/bin/env python3
"""
Современные тесты для основных функций Telegram бота
"""

import pytest
from unittest.mock import patch, AsyncMock
import sys
import os

# Add the project root to the python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from telegram import InlineKeyboardMarkup
from bot import start, help_command


@pytest.mark.asyncio
async def test_start_command(mock_telegram_update, mock_telegram_context):
    """Тест команды /start"""
    from bot import start, help_command
    
    await start(mock_telegram_update, mock_telegram_context)
    
    # Проверяем что бот ответил
    mock_telegram_update.message.reply_text.assert_called_once()
    call_args = mock_telegram_update.message.reply_text.call_args
    
    # Проверяем содержимое ответа
    assert "Добро пожаловать" in call_args[0][0]
    # Клавиатура должна быть InlineKeyboardMarkup, а не строка
    assert call_args[1]["reply_markup"] is not None


@pytest.mark.asyncio
async def test_help_command(mock_telegram_update, mock_telegram_context):
    """Тестирует команду /help"""
    mock_telegram_update.message.reply_text = AsyncMock()

    await help_command(mock_telegram_update, mock_telegram_context)

    mock_telegram_update.message.reply_text.assert_called_once()
    call_args = mock_telegram_update.message.reply_text.call_args
    assert "Справка по использованию" in call_args[0][0]
    assert isinstance(call_args[1]["reply_markup"], InlineKeyboardMarkup)
    assert call_args[1]["parse_mode"] == "Markdown"
