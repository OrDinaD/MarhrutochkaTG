"""
Менеджер аккаунтов пользователей для автопокупки билетов.
Хранит учетные данные пользователей (зашифрованные).
"""

import json
import logging
from typing import Optional, Dict
from pathlib import Path
import hashlib
import os

logger = logging.getLogger(__name__)


class AccountManager:
    """Управление аккаунтами пользователей"""

    def __init__(self, storage_file: str = "data/user_accounts.json"):
        """
        Инициализация менеджера аккаунтов.
        
        Args:
            storage_file: Путь к файлу хранения аккаунтов
        """
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.accounts: Dict[int, Dict] = {}
        self._load_accounts()

    def _get_encryption_key(self) -> bytes:
        """
        Получить ключ шифрования.
        В production следует использовать переменную окружения.
        """
        key = os.getenv('ENCRYPTION_KEY', 'default_key_change_in_production')
        return key.encode()

    def _encrypt(self, data: str) -> str:
        """
        Простое шифрование данных (для production использовать cryptography).
        
        Args:
            data: Данные для шифрования
            
        Returns:
            Зашифрованные данные
        """
        # Простое XOR шифрование (для production использовать cryptography.fernet)
        key = self._get_encryption_key()
        encrypted = []
        
        for i, char in enumerate(data):
            key_char = key[i % len(key)]
            encrypted_char = chr(ord(char) ^ key_char)
            encrypted.append(encrypted_char)
        
        return ''.join(encrypted).encode().hex()

    def _decrypt(self, encrypted_data: str) -> str:
        """
        Расшифровать данные.
        
        Args:
            encrypted_data: Зашифрованные данные
            
        Returns:
            Расшифрованные данные
        """
        try:
            data = bytes.fromhex(encrypted_data).decode()
            key = self._get_encryption_key()
            decrypted = []
            
            for i, char in enumerate(data):
                key_char = key[i % len(key)]
                decrypted_char = chr(ord(char) ^ key_char)
                decrypted.append(decrypted_char)
            
            return ''.join(decrypted)
        except Exception as e:
            logger.error(f"Ошибка расшифровки: {e}")
            return ""

    def _load_accounts(self):
        """Загрузить аккаунты из файла"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Преобразуем ключи обратно в int
                    self.accounts = {int(k): v for k, v in data.items()}
                logger.info(f"Загружено аккаунтов: {len(self.accounts)}")
            else:
                logger.info("Файл аккаунтов не найден, создается новый")
                self.accounts = {}
        except Exception as e:
            logger.error(f"Ошибка загрузки аккаунтов: {e}")
            self.accounts = {}

    def _save_accounts(self):
        """Сохранить аккаунты в файл"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, ensure_ascii=False, indent=2)
            logger.info("Аккаунты сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения аккаунтов: {e}")

    def add_account(self, user_id: int, phone: str, password: str) -> bool:
        """
        Добавить или обновить аккаунт пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            phone: Номер телефона
            password: Пароль
            
        Returns:
            True если успешно
        """
        try:
            self.accounts[user_id] = {
                'phone': self._encrypt(phone),
                'password': self._encrypt(password),
                'has_account': True
            }
            self._save_accounts()
            logger.info(f"Аккаунт добавлен для пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления аккаунта: {e}")
            return False

    def get_account(self, user_id: int) -> Optional[Dict[str, str]]:
        """
        Получить учетные данные пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            Словарь с phone и password или None
        """
        try:
            if user_id in self.accounts:
                account = self.accounts[user_id]
                return {
                    'phone': self._decrypt(account['phone']),
                    'password': self._decrypt(account['password'])
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка получения аккаунта: {e}")
            return None

    def has_account(self, user_id: int) -> bool:
        """
        Проверить, есть ли у пользователя сохраненный аккаунт.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            True если аккаунт есть
        """
        return user_id in self.accounts and self.accounts[user_id].get('has_account', False)

    def remove_account(self, user_id: int) -> bool:
        """
        Удалить аккаунт пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            True если успешно
        """
        try:
            if user_id in self.accounts:
                del self.accounts[user_id]
                self._save_accounts()
                logger.info(f"Аккаунт удален для пользователя {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка удаления аккаунта: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        Получить статистику по аккаунтам.
        
        Returns:
            Словарь со статистикой
        """
        return {
            'total_accounts': len(self.accounts),
            'users_with_accounts': len([a for a in self.accounts.values() if a.get('has_account')])
        }
