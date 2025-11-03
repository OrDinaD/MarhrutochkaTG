import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot import handle_main_menu, user_data_store
from telegram.ext import ConversationHandler

@pytest.mark.asyncio
async def test_handle_main_menu(mock_telegram_update, mock_telegram_context):
    """Тестирует обработчик главного меню"""
    mock_telegram_update.callback_query.from_user.id = 12345
    user_id = 12345
    user_data_store[user_id] = {'some': 'data'}

    with patch('bot.safe_edit_message', new_callable=AsyncMock) as mock_safe_edit_message:
        result = await handle_main_menu(mock_telegram_update, mock_telegram_context)

        # Проверяем что данные пользователя очищены
        assert user_id not in user_data_store
        
        # Проверяем что safe_edit_message был вызван
        mock_safe_edit_message.assert_called_once()
        
        # Проверяем что conversation завершается
        assert result == ConversationHandler.END
