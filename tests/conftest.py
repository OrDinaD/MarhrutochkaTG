#!/usr/bin/env python3
"""
Конфигурация pytest с fixtures для тестирования Telegram бота
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Добавляем src в путь для импортов
PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Создаём папки для тестов если их нет
os.makedirs(PROJECT_ROOT / "data" / "logs", exist_ok=True)
os.makedirs(PROJECT_ROOT / "data" / "temp", exist_ok=True)

@pytest.fixture(scope="session")
def event_loop():
    """Создаём event loop для всей сессии тестов"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_env():
    """Мокаем переменные окружения для тестов"""
    test_env = {
        'TELEGRAM_BOT_TOKEN': 'test_token_123456789:AAH1234567890',
        'ADMIN_TELEGRAM_ID': '123456789',
        'TEST_MODE': 'true',
        'DATABASE_URL': 'sqlite:///:memory:'
    }
    
    with patch.dict(os.environ, test_env):
        yield test_env

@pytest.fixture
def mock_telegram_update():
    """Создаём мок Telegram Update объекта"""
    update = Mock()
    update.message = Mock()
    update.message.reply_text = AsyncMock()
    update.message.reply_markup = AsyncMock()
    update.message.from_user = Mock()
    update.message.from_user.id = 12345
    update.message.from_user.username = "test_user"
    update.message.from_user.first_name = "Test"
    
    update.callback_query = Mock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.from_user = Mock()
    update.callback_query.from_user.id = 12345
    
    return update

@pytest.fixture  
def mock_telegram_context():
    """Создаём мок Telegram Context объекта"""
    context = Mock()
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    context.args = []
    
    context.bot = Mock()
    context.bot.send_message = AsyncMock()
    context.bot.edit_message_text = AsyncMock()
    
    return context

@pytest.fixture
def mock_database():
    """Мокаем базу данных"""
    mock_db = Mock()
    mock_db.user_exists = Mock(return_value=True)
    mock_db.save_user = Mock()
    mock_db.get_user = Mock(return_value={'id': 12345, 'username': 'test_user'})
    return mock_db

@pytest.fixture
def mock_parser():
    """Мокаем парсер маршрутов"""
    with patch('src.utils.FinalMarshrutochkaParser') as mock_parser_class:
        parser = Mock()
        parser.search_routes = Mock(return_value={
            'success': True,
            'routes': [
                {
                    'id': '1',
                    'number': '123',
                    'direction': 'Центр - Окраина',
                    'schedule': ['08:00', '08:30', '09:00']
                }
            ]
        })
        mock_parser_class.return_value = parser
        yield parser

@pytest.fixture
def mock_monitoring():
    """Мокаем систему мониторинга"""
    with patch('src.monitoring.railway_logger') as mock_logger, \
         patch('src.monitoring.crash_handler') as mock_crash, \
         patch('src.monitoring.setup_logging') as mock_setup:
        
        mock_logger.info = Mock()
        mock_logger.error = Mock()
        mock_logger.warning = Mock()
        
        mock_crash.handle_exception = Mock()
        mock_setup.return_value = Mock()
        
        yield {
            'logger': mock_logger,
            'crash_handler': mock_crash,
            'setup_logging': mock_setup
        }

@pytest.fixture
def mock_keyboards():
    """Мокаем фабрику клавиатур"""
    with patch('src.utils.keyboards.keyboard_factory') as mock_factory:
        mock_factory.get_main_menu_keyboard = Mock()
        mock_factory.get_date_keyboard = Mock()
        mock_factory.get_direction_keyboard = Mock()
        yield mock_factory

@pytest.fixture
def mock_user_manager():
    """Мокаем менеджер пользователей"""
    mock_manager = Mock()
    mock_manager.get_user = Mock(return_value={'id': 12345})
    mock_manager.save_user = Mock()
    mock_manager.create_user = Mock()
    return mock_manager

@pytest.fixture
def clean_test_data():
    """Очищает тестовые данные после каждого теста"""
    yield
    # Очистка после теста
    test_files = [
        PROJECT_ROOT / "data" / "logs" / "test.log",
        PROJECT_ROOT / "data" / "temp" / "test.json"
    ]
    for file in test_files:
        if file.exists():
            file.unlink()

@pytest.fixture(autouse=True) 
def setup_test_environment(mock_env, clean_test_data):
    """Автоматически настраивает тестовое окружение для каждого теста"""
    # Настройка выполняется автоматически через mock_env и clean_test_data
    yield
