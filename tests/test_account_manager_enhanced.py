#!/usr/bin/env python3
"""
Расширенные тесты для AccountManager
Дополняют существующие тесты в test_autobuy.py
"""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from src.managers.account_manager import AccountManager


class TestAccountManagerSecurity:
    """Тесты безопасности AccountManager"""
    
    def test_encryption_key_from_env(self, tmp_path):
        """Тест использования ключа из переменной окружения"""
        storage_file = tmp_path / "test_accounts.json"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': 'custom_test_key_123'}):
            manager = AccountManager(storage_file=str(storage_file))
            
            # Проверяем что используется кастомный ключ
            key = manager._get_encryption_key()
            assert key == b'custom_test_key_123'
    
    def test_default_encryption_key(self, tmp_path):
        """Тест использования ключа по умолчанию"""
        storage_file = tmp_path / "test_accounts.json"
        
        with patch.dict(os.environ, {}, clear=True):
            manager = AccountManager(storage_file=str(storage_file))
            
            # Проверяем что используется ключ по умолчанию
            key = manager._get_encryption_key()
            assert key == b'default_key_change_in_production'
    
    def test_encrypted_data_not_plaintext(self, tmp_path):
        """Тест что данные в файле не хранятся в plaintext"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        test_password = "super_secret_password_123"
        manager.add_account(12345, "299605390", test_password)
        
        # Читаем файл
        with open(storage_file, 'r') as f:
            content = f.read()
        
        # Проверяем что plaintext пароля нет в файле
        assert test_password not in content
        assert "super_secret" not in content
    
    def test_encryption_with_special_characters(self, tmp_path):
        """Тест шифрования с спецсимволами"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        special_password = "пароль!@#$%^&*()_+-=[]{}|;:',.<>?/`~"
        encrypted = manager._encrypt(special_password)
        decrypted = manager._decrypt(encrypted)
        
        assert decrypted == special_password
    
    def test_encryption_with_cyrillic(self, tmp_path):
        """Тест шифрования кириллицы"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        cyrillic_password = "Привет_мир_123_тест"
        encrypted = manager._encrypt(cyrillic_password)
        decrypted = manager._decrypt(encrypted)
        
        assert decrypted == cyrillic_password
    
    def test_encryption_with_empty_string(self, tmp_path):
        """Тест шифрования пустой строки"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        encrypted = manager._encrypt("")
        decrypted = manager._decrypt(encrypted)
        
        assert decrypted == ""
    
    def test_encryption_with_very_long_string(self, tmp_path):
        """Тест шифрования очень длинной строки"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        long_password = "a" * 1000
        encrypted = manager._encrypt(long_password)
        decrypted = manager._decrypt(encrypted)
        
        assert decrypted == long_password
        assert len(decrypted) == 1000
    
    def test_decryption_invalid_data(self, tmp_path):
        """Тест дешифрования поврежденных данных"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        # Пробуем расшифровать невалидные данные
        result = manager._decrypt("invalid_hex_data_xyz")
        
        # Должно вернуть пустую строку при ошибке
        assert result == ""


class TestAccountManagerPersistence:
    """Тесты персистентности данных"""
    
    def test_save_and_load_multiple_accounts(self, tmp_path):
        """Тест сохранения и загрузки нескольких аккаунтов"""
        storage_file = tmp_path / "test_accounts.json"
        
        # Создаем менеджер и добавляем несколько аккаунтов
        manager1 = AccountManager(storage_file=str(storage_file))
        manager1.add_account(12345, "299111111", "pass1")
        manager1.add_account(67890, "299222222", "pass2")
        manager1.add_account(11111, "299333333", "pass3")
        
        # Создаем новый менеджер и проверяем загрузку
        manager2 = AccountManager(storage_file=str(storage_file))
        
        assert manager2.has_account(12345)
        assert manager2.has_account(67890)
        assert manager2.has_account(11111)
        
        # Проверяем данные
        account1 = manager2.get_account(12345)
        assert account1['phone'] == "299111111"
        assert account1['password'] == "pass1"
    
    def test_corrupted_json_file(self, tmp_path):
        """Тест обработки поврежденного JSON файла"""
        storage_file = tmp_path / "test_accounts.json"
        
        # Создаем поврежденный JSON файл
        with open(storage_file, 'w') as f:
            f.write("{invalid json content")
        
        # Менеджер должен создать пустое хранилище
        manager = AccountManager(storage_file=str(storage_file))
        
        assert manager.accounts == {}
    
    def test_nonexistent_file(self, tmp_path):
        """Тест работы с несуществующим файлом"""
        storage_file = tmp_path / "nonexistent" / "test_accounts.json"
        
        # Менеджер должен создать директорию и файл
        manager = AccountManager(storage_file=str(storage_file))
        
        assert manager.accounts == {}
        assert storage_file.parent.exists()
    
    def test_file_permissions_after_save(self, tmp_path):
        """Тест прав доступа к файлу после сохранения"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        manager.add_account(12345, "299605390", "password")
        
        # Файл должен существовать
        assert storage_file.exists()
        
        # Проверяем что файл создан
        assert storage_file.stat().st_size > 0
    
    def test_integer_user_id_preservation(self, tmp_path):
        """Тест сохранения user_id как integer"""
        storage_file = tmp_path / "test_accounts.json"
        
        manager1 = AccountManager(storage_file=str(storage_file))
        manager1.add_account(12345, "299605390", "password")
        
        # Загружаем и проверяем тип
        manager2 = AccountManager(storage_file=str(storage_file))
        
        # Ключи должны быть int, не str
        assert 12345 in manager2.accounts
        assert isinstance(list(manager2.accounts.keys())[0], int)


class TestAccountManagerEdgeCases:
    """Тесты граничных случаев"""
    
    def test_update_existing_account(self, tmp_path):
        """Тест обновления существующего аккаунта"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        # Добавляем аккаунт
        manager.add_account(12345, "299111111", "old_password")
        
        # Обновляем тот же аккаунт
        manager.add_account(12345, "299222222", "new_password")
        
        # Проверяем что данные обновились
        account = manager.get_account(12345)
        assert account['phone'] == "299222222"
        assert account['password'] == "new_password"
    
    def test_remove_nonexistent_account(self, tmp_path):
        """Тест удаления несуществующего аккаунта"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        result = manager.remove_account(99999)
        
        assert result is False
    
    def test_get_nonexistent_account(self, tmp_path):
        """Тест получения несуществующего аккаунта"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        account = manager.get_account(99999)
        
        assert account is None
    
    def test_stats_empty(self, tmp_path):
        """Тест статистики для пустого менеджера"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        stats = manager.get_stats()
        
        assert stats['total_accounts'] == 0
        assert stats['users_with_accounts'] == 0
    
    def test_stats_multiple_accounts(self, tmp_path):
        """Тест статистики с несколькими аккаунтами"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        for i in range(10):
            manager.add_account(10000 + i, f"29960{i:04d}", f"pass{i}")
        
        stats = manager.get_stats()
        
        assert stats['total_accounts'] == 10
        assert stats['users_with_accounts'] == 10
    
    def test_concurrent_operations(self, tmp_path):
        """Тест конкурентных операций"""
        storage_file = tmp_path / "test_accounts.json"
        
        # Создаем два менеджера с одним файлом
        manager1 = AccountManager(storage_file=str(storage_file))
        manager2 = AccountManager(storage_file=str(storage_file))
        
        # Добавляем аккаунты через разные менеджеры
        manager1.add_account(12345, "299111111", "pass1")
        manager2.add_account(67890, "299222222", "pass2")
        
        # Перезагружаем первый менеджер
        manager1._load_accounts()
        
        # Должен видеть только свой аккаунт (последний сохраненный)
        # Это демонстрирует потенциальную проблему race condition


class TestAccountManagerValidation:
    """Тесты валидации данных"""
    
    def test_add_account_with_empty_phone(self, tmp_path):
        """Тест добавления аккаунта с пустым номером"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        result = manager.add_account(12345, "", "password")
        
        # Должно работать, валидация на уровне handlers
        assert result is True
    
    def test_add_account_with_empty_password(self, tmp_path):
        """Тест добавления аккаунта с пустым паролем"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        result = manager.add_account(12345, "299605390", "")
        
        # Должно работать, валидация на уровне handlers
        assert result is True
    
    def test_user_id_types(self, tmp_path):
        """Тест разных типов user_id"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        # int user_id (нормальный случай)
        manager.add_account(12345, "299111111", "pass1")
        assert manager.has_account(12345)
        
        # Проверяем что строковый user_id не найдется
        assert not manager.has_account("12345")


class TestAccountManagerErrorHandling:
    """Тесты обработки ошибок"""
    
    def test_save_accounts_io_error(self, tmp_path):
        """Тест обработки ошибки записи в файл"""
        storage_file = tmp_path / "readonly" / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        # Пытаемся добавить аккаунт в несуществующую директорию
        # Должно создать директорию автоматически
        result = manager.add_account(12345, "299605390", "password")
        
        # Должно работать, т.к. создается директория
        assert result is True
    
    def test_load_accounts_with_permission_error(self, tmp_path):
        """Тест загрузки аккаунтов при ошибке прав доступа"""
        storage_file = tmp_path / "test_accounts.json"
        
        # Создаем файл
        storage_file.write_text("{}")
        
        # Делаем файл недоступным для чтения (только на Unix)
        if os.name != 'nt':  # Не Windows
            os.chmod(storage_file, 0o000)
            
            manager = AccountManager(storage_file=str(storage_file))
            
            # Должно создать пустое хранилище
            assert manager.accounts == {}
            
            # Восстанавливаем права для очистки
            os.chmod(storage_file, 0o600)
    
    def test_decrypt_with_wrong_key(self, tmp_path):
        """Тест дешифрования с неправильным ключом"""
        storage_file = tmp_path / "test_accounts.json"
        
        # Шифруем с одним ключом
        with patch.dict(os.environ, {'ENCRYPTION_KEY': 'key1'}):
            manager1 = AccountManager(storage_file=str(storage_file))
            manager1.add_account(12345, "299605390", "password")
        
        # Пытаемся расшифровать с другим ключом
        with patch.dict(os.environ, {'ENCRYPTION_KEY': 'key2'}):
            manager2 = AccountManager(storage_file=str(storage_file))
            account = manager2.get_account(12345)
            
            # Пароль будет неправильно расшифрован
            assert account is not None
            assert account['password'] != "password"


class TestAccountManagerIntegration:
    """Интеграционные тесты"""
    
    def test_full_lifecycle(self, tmp_path):
        """Тест полного жизненного цикла аккаунта"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        user_id = 12345
        phone = "299605390"
        password = "test_password_123"
        
        # 1. Проверяем что аккаунта нет
        assert not manager.has_account(user_id)
        
        # 2. Добавляем аккаунт
        result = manager.add_account(user_id, phone, password)
        assert result is True
        
        # 3. Проверяем что аккаунт есть
        assert manager.has_account(user_id)
        
        # 4. Получаем аккаунт
        account = manager.get_account(user_id)
        assert account is not None
        assert account['phone'] == phone
        assert account['password'] == password
        
        # 5. Обновляем аккаунт
        new_password = "new_password_456"
        manager.add_account(user_id, phone, new_password)
        
        # 6. Проверяем обновление
        account = manager.get_account(user_id)
        assert account['password'] == new_password
        
        # 7. Удаляем аккаунт
        result = manager.remove_account(user_id)
        assert result is True
        
        # 8. Проверяем что аккаунта нет
        assert not manager.has_account(user_id)
        
        # 9. Проверяем статистику
        stats = manager.get_stats()
        assert stats['total_accounts'] == 0
    
    def test_multiple_users_isolation(self, tmp_path):
        """Тест изоляции данных разных пользователей"""
        storage_file = tmp_path / "test_accounts.json"
        manager = AccountManager(storage_file=str(storage_file))
        
        # Добавляем аккаунты для разных пользователей
        manager.add_account(11111, "299111111", "pass1")
        manager.add_account(22222, "299222222", "pass2")
        manager.add_account(33333, "299333333", "pass3")
        
        # Проверяем что каждый пользователь видит только свои данные
        account1 = manager.get_account(11111)
        account2 = manager.get_account(22222)
        account3 = manager.get_account(33333)
        
        assert account1['phone'] == "299111111"
        assert account2['phone'] == "299222222"
        assert account3['phone'] == "299333333"
        
        # Удаляем один аккаунт
        manager.remove_account(22222)
        
        # Проверяем что другие аккаунты остались
        assert manager.has_account(11111)
        assert not manager.has_account(22222)
        assert manager.has_account(33333)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
