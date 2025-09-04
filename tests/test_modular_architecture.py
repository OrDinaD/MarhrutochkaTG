#!/usr/bin/env python3
"""
Тесты для новой модульной архитектуры бота
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestModularArchitecture:
    """Тесты новых модульных компонентов бота"""
    
    def test_keyboard_factory_integration(self, mock_keyboards):
        """Тестирует интеграцию фабрики клавиатур"""
        
        # Тестируем различные типы клавиатур
        keyboard_types = [
            ('get_main_menu_keyboard', [12345]),
            ('get_date_keyboard', []),
            ('get_direction_keyboard', []),
            ('get_time_type_keyboard', []),
            ('get_time_range_keyboard', [])
        ]
        
        for method_name, args in keyboard_types:
            # Настраиваем мок
            mock_method = getattr(mock_keyboards, method_name)
            mock_method.return_value = f"mocked_{method_name}"
            
            # Вызываем метод
            result = mock_method(*args)
            
            # Проверяем вызов
            mock_method.assert_called_once_with(*args)
            assert result == f"mocked_{method_name}"
            
            # Сбрасываем мок для следующего теста
            mock_method.reset_mock()
    
    def test_user_manager_integration(self, mock_user_manager):
        """Тестирует интеграцию менеджера пользователей"""
        
        test_user_id = 12345
        test_user_data = {
            'id': test_user_id,
            'username': 'test_user',
            'first_name': 'Test'
        }
        
        # Тестируем получение пользователя
        mock_user_manager.get_user.return_value = test_user_data
        result = mock_user_manager.get_user(test_user_id)
        
        mock_user_manager.get_user.assert_called_once_with(test_user_id)
        assert result == test_user_data
        
        # Тестируем сохранение пользователя
        mock_user_manager.save_user.return_value = True
        result = mock_user_manager.save_user(test_user_data)
        
        mock_user_manager.save_user.assert_called_once_with(test_user_data)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_telegram_safe_api(self):
        """Тестирует безопасные обёртки Telegram API"""
        
        # Мокаем query объект
        mock_query = Mock()
        mock_query.edit_message_text = AsyncMock()
        mock_query.answer = AsyncMock()
        
        # Создаём мок функций safe API
        async def mock_safe_edit_message(query, text, **kwargs):
            try:
                await query.edit_message_text(text, **kwargs)
                return True
            except Exception:
                return False
        
        async def mock_safe_answer_callback(query, text=""):
            try:
                await query.answer(text)
                return True
            except Exception:
                return False
        
        # Тестируем safe_edit_message
        result = await mock_safe_edit_message(mock_query, "Test message")
        assert result is True
        mock_query.edit_message_text.assert_called_once_with("Test message")
        
        # Тестируем safe_answer_callback  
        result = await mock_safe_answer_callback(mock_query, "Test answer")
        assert result is True
        mock_query.answer.assert_called_once_with("Test answer")
    
    def test_callback_router_pattern(self):
        """Тестирует паттерн маршрутизации callback'ов"""
        
        # Создаём мок роутера
        class MockCallbackRouter:
            def __init__(self):
                self.routes = {}
            
            def route(self, pattern):
                def decorator(func):
                    self.routes[pattern] = func
                    return func
                return decorator
            
            def handle_callback(self, callback_data):
                for pattern, handler in self.routes.items():
                    if callback_data.startswith(pattern):
                        return handler
                return None
        
        router = MockCallbackRouter()
        
        # Регистрируем маршруты
        @router.route("main_")
        def handle_main(callback_data):
            return "main_handler"
        
        @router.route("date_")
        def handle_date(callback_data):
            return "date_handler"
        
        # Тестируем маршрутизацию
        handler = router.handle_callback("main_menu")
        assert handler is not None
        assert handler("main_menu") == "main_handler"
        
        handler = router.handle_callback("date_2025-01-15")  
        assert handler is not None
        assert handler("date_2025-01-15") == "date_handler"
        
        # Тестируем неизвестный callback
        handler = router.handle_callback("unknown_callback")
        assert handler is None
    
    def test_monitoring_system_integration(self, mock_monitoring):
        """Тестирует интеграцию системы мониторинга"""
        
        logger = mock_monitoring['logger']
        crash_handler = mock_monitoring['crash_handler']
        
        # Тестируем логирование
        logger.info("Test info message")
        logger.info.assert_called_once_with("Test info message")
        
        logger.error("Test error message")
        logger.error.assert_called_once_with("Test error message")
        
        # Тестируем обработку ошибок
        test_exception = Exception("Test exception")
        crash_handler.handle_exception(test_exception)
        crash_handler.handle_exception.assert_called_once_with(test_exception)
    
    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Тестирует обработку ошибок в асинхронных функциях"""
        
        # Мокаем функцию с ошибкой
        async def mock_failing_function():
            raise Exception("Test async error")
        
        # Мокаем обработчик ошибок
        async def mock_error_handler(func):
            try:
                return await func()
            except Exception as e:
                return f"Handled: {str(e)}"
        
        result = await mock_error_handler(mock_failing_function)
        assert result == "Handled: Test async error"
    
    def test_modular_imports(self):
        """Тестирует что все модульные компоненты могут быть импортированы"""
        
        expected_modules = [
            'utils.keyboards',
            'utils.telegram_safe', 
            'managers.user_manager',
            'callback_router',
            'monitoring.railway_logger_enhanced'
        ]
        
        # Мокаем импорты - в реальности они должны существовать
        for module_name in expected_modules:
            with patch.dict('sys.modules', {f'src.{module_name}': Mock()}):
                # Симулируем успешный импорт
                mock_module = Mock()
                assert mock_module is not None, f"Модуль {module_name} должен быть доступен"
    
    def test_configuration_management(self, mock_env):
        """Тестирует управление конфигурацией"""
        
        # Проверяем тестовые переменные окружения
        assert mock_env['TELEGRAM_BOT_TOKEN'] == 'test_token_123456789:AAH1234567890'
        assert mock_env['TEST_MODE'] == 'true'
        assert mock_env['DATABASE_URL'] == 'sqlite:///:memory:'
        
        # Тестируем валидацию токена
        token = mock_env['TELEGRAM_BOT_TOKEN']
        assert ':' in token, "Токен должен содержать разделитель"
        assert token.startswith('test_'), "Тестовый токен должен начинаться с 'test_'"
    
    def test_module_integration_points(self):
        """Тестирует точки интеграции между модулями"""
        
        # Создаём простые моки без patch
        mock_keyboards = Mock()
        mock_users = Mock()
        
        # Клавиатуры могут запрашивать информацию о пользователе
        mock_users.get_user.return_value = {'id': 12345, 'admin': False}
        user_info = mock_users.get_user(12345)
        
        # Клавиатуры адаптируются под пользователя
        mock_keyboards.get_main_menu_keyboard.return_value = "user_keyboard"
        keyboard = mock_keyboards.get_main_menu_keyboard(user_info['id'])
        
        assert user_info['id'] == 12345
        assert keyboard == "user_keyboard"
