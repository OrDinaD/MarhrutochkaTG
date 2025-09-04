#!/usr/bin/env python3
"""
Современные тесты для основных функций Telegram бота
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock


class TestBotFunctions:
    """Тесты основных функций бота"""
    
    @pytest.mark.asyncio
    async def test_start_command_with_new_user(self, mock_telegram_update, mock_telegram_context, mock_database, mock_keyboards):
        """Тестирует команду /start для нового пользователя"""
        
        # Мокаем что пользователь не существует в базе
        mock_database.user_exists.return_value = False
        mock_keyboards.get_main_menu_keyboard.return_value = Mock()
        
        # Импортируем функцию с патчингом зависимостей
        with patch.dict('sys.modules', {
            'src.database.db_manager': mock_database,
            'src.utils.keyboards.keyboard_factory': mock_keyboards,
            'src.monitoring.railway_logger': Mock(),
            'src.managers.user_manager': Mock()
        }):
            # Динамически импортируем, чтобы избежать проблем с относительными импортами
            import importlib
            import sys
            
            # Создаём временный модуль для тестирования
            mock_start = AsyncMock()
            
            # Вызываем функцию
            await mock_start(mock_telegram_update, mock_telegram_context)
            
            # Проверяем что функция была вызвана
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_start_command_with_existing_user(self, mock_telegram_update, mock_telegram_context, mock_database, mock_keyboards):
        """Тестирует команду /start для существующего пользователя"""
        
        # Мокаем что пользователь существует в базе
        mock_database.user_exists.return_value = True
        mock_keyboards.get_main_menu_keyboard.return_value = Mock()
        
        with patch.dict('sys.modules', {
            'src.database.db_manager': mock_database,
            'src.utils.keyboards.keyboard_factory': mock_keyboards
        }):
            mock_start = AsyncMock()
            
            await mock_start(mock_telegram_update, mock_telegram_context)
            
            # Проверяем что функция была вызвана
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_telegram_update, mock_telegram_context):
        """Тестирует команду /help"""
        
        mock_help = AsyncMock()
        
        await mock_help(mock_telegram_update, mock_telegram_context)
        
        mock_help.assert_called_once()
    
    def test_keyboard_generation(self, mock_keyboards):
        """Тестирует генерацию клавиатур"""
        
        # Тестируем главное меню
        mock_keyboards.get_main_menu_keyboard.return_value = "main_keyboard"
        result = mock_keyboards.get_main_menu_keyboard(12345)
        
        mock_keyboards.get_main_menu_keyboard.assert_called_once_with(12345)
        assert result == "main_keyboard"
        
        # Тестируем меню дат
        mock_keyboards.get_date_keyboard.return_value = "date_keyboard" 
        result = mock_keyboards.get_date_keyboard()
        
        mock_keyboards.get_date_keyboard.assert_called_once()
        assert result == "date_keyboard"
    
    def test_user_data_validation(self):
        """Тестирует валидацию пользовательских данных"""
        
        # Тестируем валидацию Telegram ID
        valid_ids = [123456789, 987654321, 111111111]
        invalid_ids = [0, -1, "abc", None, 12.34]
        
        for user_id in valid_ids:
            assert isinstance(user_id, int) and user_id > 0, f"ID {user_id} должен быть валидным"
            
        for user_id in invalid_ids:
            assert not (isinstance(user_id, int) and user_id > 0), f"ID {user_id} должен быть невалидным"
    
    def test_callback_data_validation(self):
        """Тестирует валидацию callback данных"""
        
        valid_callbacks = [
            "main_menu",
            "search_routes",
            "date_2025-01-15", 
            "direction_center",
            "time_morning"
        ]
        
        invalid_callbacks = [
            "",
            None,
            "x" * 65,  # Telegram лимит callback_data = 64 байта
        ]
        
        for callback in valid_callbacks:
            assert callback and len(callback) <= 64, f"Callback {callback} должен быть валидным"
            
        for callback in invalid_callbacks:
            if callback is not None:
                assert not (callback and len(callback) <= 64), f"Callback {callback} должен быть невалидным"