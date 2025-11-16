"""
Менеджер аккаунтов пользователей для автопокупки билетов.
Хранит учетные данные пользователей (зашифрованные).
"""

import base64
import json
import logging
from typing import Optional, Dict
from pathlib import Path
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

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
        self._raw_encryption_key = os.getenv('ENCRYPTION_KEY', 'default_key_change_in_production')
        self._cipher: Optional[Fernet] = None
        self._legacy_key = self._raw_encryption_key.encode()
        self._load_accounts()

    def _derive_fernet_key(self) -> bytes:
        """Формирует корректный ключ для Fernet на основе исходной секретной строки."""
        digest = hashlib.sha256(self._raw_encryption_key.encode()).digest()
        return base64.urlsafe_b64encode(digest)

    def _get_cipher(self) -> Fernet:
        """Лениво создает и кеширует экземпляр Fernet."""
        if not self._cipher:
            self._cipher = Fernet(self._derive_fernet_key())
        return self._cipher

    def _encrypt(self, data: str) -> str:
        """Шифрует данные с использованием Fernet."""
        cipher = self._get_cipher()
        token = cipher.encrypt(data.encode('utf-8'))
        return token.decode('utf-8')

    def _legacy_decrypt(self, encrypted_data: str) -> Optional[str]:
        """Расшифровывает данные, сохраненные старым XOR-алгоритмом."""
        try:
            raw = bytes.fromhex(encrypted_data).decode()
        except ValueError:
            return None
        decrypted = []
        for i, char in enumerate(raw):
            key_char = self._legacy_key[i % len(self._legacy_key)]
            decrypted_char = chr(ord(char) ^ key_char)
            decrypted.append(decrypted_char)
        return ''.join(decrypted)

    def _decrypt_value(self, encrypted_data: str) -> tuple[str, bool]:
        """Возвращает расшифрованное значение и флаг необходимости миграции."""
        if not encrypted_data:
            return "", False
        cipher = self._get_cipher()
        try:
            decrypted = cipher.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
            return decrypted, False
        except InvalidToken:
            legacy_value = self._legacy_decrypt(encrypted_data)
            if legacy_value is not None:
                logger.warning("Обнаружены учетные данные, зашифрованные устаревшим методом. Выполняем миграцию.")
                return legacy_value, True
            logger.error("Не удалось расшифровать данные: неверный формат токена")
        except Exception as e:
            logger.error(f"Ошибка расшифровки: {e}")
        return "", False

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
                phone, phone_legacy = self._decrypt_value(account.get('phone', ''))
                password, password_legacy = self._decrypt_value(account.get('password', ''))

                if phone_legacy or password_legacy:
                    account['phone'] = self._encrypt(phone)
                    account['password'] = self._encrypt(password)
                    self._save_accounts()

                if phone and password:
                    return {'phone': phone, 'password': password}
                logger.error(f"Не удалось расшифровать данные аккаунта пользователя {user_id}")
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
