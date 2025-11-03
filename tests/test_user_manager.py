#!/usr/bin/env python3
"""
Тесты для менеджера пользователей
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from managers.user_manager import UserManager


class TestUserManager:
    """Тесты менеджера пользователей"""
    
    def test_user_manager_init(self):
        """Тест инициализации менеджера пользователей"""
        manager = UserManager()
        
        assert manager.user_data_store == {}
        assert manager.active_monitors == {}
        assert manager.storage is None
    
    def test_clear_user_temp_data(self):
        """Тест очистки временных данных пользователя"""
        manager = UserManager()
        user_id = 12345
        
        # Добавляем данные
        manager.user_data_store[user_id] = {'some': 'data'}
        
        # Очищаем
        manager.clear_user_temp_data(user_id)
        
        assert user_id not in manager.user_data_store
    
    def test_clear_user_temp_data_nonexistent(self):
        """Тест очистки данных несуществующего пользователя"""
        manager = UserManager()
        
        # Не должно вызывать ошибок
        manager.clear_user_temp_data(99999)
    
    def test_get_user_monitor_exists(self):
        """Тест получения существующего мониторинга"""
        manager = UserManager()
        user_id = 12345
        
        monitor_config = {
            'direction': 'minsk_ostrovets',
            'date': '2025-11-03'
        }
        
        manager.active_monitors[user_id] = monitor_config
        
        result = manager.get_user_monitor(user_id)
        
        assert result == monitor_config
    
    def test_get_user_monitor_not_exists(self):
        """Тест получения несуществующего мониторинга"""
        manager = UserManager()
        
        result = manager.get_user_monitor(99999)
        
        assert result is None
    
    def test_set_user_monitor(self):
        """Тест установки мониторинга для пользователя"""
        manager = UserManager()
        user_id = 12345
        
        monitor_config = {
            'direction': 'minsk_ostrovets',
            'date': '2025-11-03',
            'time_type': 'departure'
        }
        
        manager.set_user_monitor(user_id, monitor_config)
        
        # Проверяем что мониторинг установлен
        assert user_id in manager.active_monitors
        
        # Проверяем что добавлены метаданные
        saved_config = manager.active_monitors[user_id]
        assert 'created_at' in saved_config
        assert 'user_id' in saved_config
        assert saved_config['user_id'] == user_id
        assert saved_config['direction'] == 'minsk_ostrovets'
    
    def test_set_user_monitor_with_storage(self):
        """Тест установки мониторинга с сохранением в storage"""
        manager = UserManager()
        
        # Мокаем storage
        mock_storage = Mock()
        mock_storage.save_monitor = Mock()
        manager.storage = mock_storage
        
        user_id = 12345
        monitor_config = {'direction': 'minsk_ostrovets'}
        
        manager.set_user_monitor(user_id, monitor_config)
        
        # Проверяем что storage был вызван
        mock_storage.save_monitor.assert_called_once()
    
    def test_set_user_monitor_storage_error(self):
        """Тест установки мониторинга при ошибке storage"""
        manager = UserManager()
        
        # Мокаем storage с ошибкой
        mock_storage = Mock()
        mock_storage.save_monitor = Mock(side_effect=Exception("Storage error"))
        manager.storage = mock_storage
        
        user_id = 12345
        monitor_config = {'direction': 'minsk_ostrovets'}
        
        # Не должно вызывать ошибку, только логировать
        manager.set_user_monitor(user_id, monitor_config)
        
        # Мониторинг всё равно должен быть установлен в памяти
        assert user_id in manager.active_monitors
    
    def test_remove_user_monitor_exists(self):
        """Тест удаления существующего мониторинга"""
        manager = UserManager()
        user_id = 12345
        
        manager.active_monitors[user_id] = {'direction': 'minsk_ostrovets'}
        
        result = manager.remove_user_monitor(user_id)
        
        assert result is True
        assert user_id not in manager.active_monitors
    
    def test_remove_user_monitor_not_exists(self):
        """Тест удаления несуществующего мониторинга"""
        manager = UserManager()
        
        result = manager.remove_user_monitor(99999)
        
        assert result is False
    
    def test_remove_user_monitor_with_storage(self):
        """Тест удаления мониторинга с очисткой storage"""
        manager = UserManager()
        
        # Мокаем storage
        mock_storage = Mock()
        mock_storage.delete_monitor = Mock()
        manager.storage = mock_storage
        
        user_id = 12345
        manager.active_monitors[user_id] = {'direction': 'minsk_ostrovets'}
        
        manager.remove_user_monitor(user_id)
        
        # Проверяем что storage был вызван
        mock_storage.delete_monitor.assert_called_once_with(user_id)
    
    def test_bind_active_monitors(self):
        """Тест привязки внешнего хранилища мониторингов"""
        manager = UserManager()
        
        external_storage = {
            12345: {'direction': 'minsk_ostrovets'},
            67890: {'direction': 'ostrovets_minsk'}
        }
        
        manager.bind_active_monitors(external_storage)
        
        # Проверяем что storage привязан
        assert manager.active_monitors is external_storage
    
    def test_bind_user_data_store(self):
        """Тест привязки внешнего хранилища данных пользователей"""
        manager = UserManager()
        
        external_storage = {
            12345: {'some': 'data'},
            67890: {'other': 'data'}
        }
        
        manager.bind_user_data_store(external_storage)
        
        # Проверяем что storage привязан
        assert manager.user_data_store is external_storage
    
    def test_emergency_reset_user(self):
        """Тест экстренного сброса пользователя"""
        manager = UserManager()
        user_id = 12345
        
        # Создаём данные
        manager.user_data_store[user_id] = {'some': 'data'}
        manager.active_monitors[user_id] = {'direction': 'minsk_ostrovets'}
        
        # Выполняем сброс
        manager.emergency_reset_user(user_id)
        
        # Проверяем что всё очищено
        assert user_id not in manager.user_data_store
        assert user_id not in manager.active_monitors
    
    def test_emergency_reset_user_with_error(self):
        """Тест экстренного сброса при ошибке"""
        manager = UserManager()
        
        # Мокаем метод удаления с ошибкой
        with patch.object(manager, 'remove_user_monitor', side_effect=Exception("Error")):
            # Не должно вызывать ошибку, только логировать
            manager.emergency_reset_user(12345)
    
    def test_set_storage(self):
        """Тест установки персистентного хранилища"""
        manager = UserManager()
        
        mock_storage = Mock()
        manager.set_storage(mock_storage)
        
        assert manager.storage is mock_storage


class TestUserManagerEdgeCases:
    """Тесты граничных случаев менеджера пользователей"""
    
    def test_multiple_users_management(self):
        """Тест управления несколькими пользователями одновременно"""
        manager = UserManager()
        
        # Добавляем несколько пользователей
        users = [12345, 67890, 11111, 22222]
        for user_id in users:
            manager.set_user_monitor(user_id, {'direction': 'minsk_ostrovets'})
        
        # Проверяем что все добавлены
        assert len(manager.active_monitors) == 4
        
        # Удаляем одного
        manager.remove_user_monitor(12345)
        
        assert len(manager.active_monitors) == 3
        assert 12345 not in manager.active_monitors
    
    def test_overwrite_existing_monitor(self):
        """Тест перезаписи существующего мониторинга"""
        manager = UserManager()
        user_id = 12345
        
        # Устанавливаем первый мониторинг
        manager.set_user_monitor(user_id, {'direction': 'minsk_ostrovets'})
        
        # Перезаписываем
        manager.set_user_monitor(user_id, {'direction': 'ostrovets_minsk'})
        
        # Проверяем что обновился
        monitor = manager.get_user_monitor(user_id)
        assert monitor['direction'] == 'ostrovets_minsk'
    
    def test_monitor_created_at_timestamp(self):
        """Тест добавления timestamp при создании мониторинга"""
        manager = UserManager()
        user_id = 12345
        
        before = datetime.now()
        manager.set_user_monitor(user_id, {'direction': 'minsk_ostrovets'})
        after = datetime.now()
        
        monitor = manager.get_user_monitor(user_id)
        
        # Проверяем что created_at в нужном диапазоне
        created_at = datetime.fromisoformat(monitor['created_at'])
        assert before <= created_at <= after
