#!/usr/bin/env python3
"""
Модуль для управления пользователями и их данными
Использует современные практики python-telegram-bot без внешней БД
"""
import logging
from typing import Dict, Optional, TYPE_CHECKING, Any
from datetime import datetime

if TYPE_CHECKING:
    # Только для типов, чтобы избежать обязательного импорта во время рантайма
    from src.storage import MonitoringStorage as _MonitoringStorage  # pragma: no cover

logger = logging.getLogger(__name__)


class UserManager:
    """
    Класс для управления пользователями и их данными.
    Использует локальное хранение данных в памяти для максимальной производительности.
    """
    
    def __init__(self):
        self.user_data_store = {}  # Локальное хранилище для временных данных
        self.active_monitors = {}  # Активные мониторинги
        self.storage: Optional[Any] = None  # Персистентное хранилище (опционально)
        
        logger.info("UserManager инициализирован в memory-only режиме")
    
    def clear_user_temp_data(self, user_id: int):
        """Очищает временные данные пользователя из локального хранилища"""
        if self.user_data_store.pop(user_id, None):
            logger.debug(f"Очищены временные данные для пользователя {user_id}")
    
    def get_user_monitor(self, user_id: int) -> Optional[dict]:
        """Получает конфигурацию мониторинга пользователя"""
        return self.active_monitors.get(user_id)
    
    def set_user_monitor(self, user_id: int, monitor_config: dict):
        """
        Устанавливает мониторинг для пользователя.
        Использует только локальное хранение в памяти для максимальной производительности.
        """
        # Добавляем метаданные
        monitor_config['created_at'] = datetime.now().isoformat()
        monitor_config['user_id'] = user_id
        
        self.active_monitors[user_id] = monitor_config
        # Сохраняем в персистентное хранилище, если доступно
        try:
            if self.storage:
                self.storage.save_monitor(user_id, monitor_config)
        except Exception as e:
            logger.error(f"Ошибка сохранения мониторинга в storage для {user_id}: {e}")
        
        logger.info(f"Установлен мониторинг для пользователя {user_id}")
    
    def remove_user_monitor(self, user_id: int) -> bool:
        """Удаляет мониторинг пользователя из локального хранилища"""
        if user_id in self.active_monitors:
            del self.active_monitors[user_id]
            try:
                if self.storage:
                    self.storage.delete_monitor(user_id)
            except Exception as e:
                logger.error(f"Ошибка удаления мониторинга из storage для {user_id}: {e}")
            logger.info(f"Удален мониторинг пользователя {user_id}")
            return True
        return False

    def bind_active_monitors(self, storage: Dict[int, dict]):
        """Связывает внешнее хранилище активных мониторингов"""
        self.active_monitors = storage

    def bind_user_data_store(self, storage: Dict[int, dict]):
        """Связывает внешнее хранилище пользовательских данных"""
        self.user_data_store = storage
    
    def emergency_reset_user(self, user_id: int):
        """
        Экстренный сброс всех данных пользователя.
        Очищает как временные данные, так и мониторинги.
        """
        try:
            # Очищаем временные данные
            self.clear_user_temp_data(user_id)
            
            # Удаляем мониторинг
            self.remove_user_monitor(user_id)
            
            logger.warning(f"Выполнен экстренный сброс для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при экстренном сбросе пользователя {user_id}: {e}")

    # ------- Интеграция со storage -------
    def set_storage(self, storage: Any):
        """Устанавливает персистентное хранилище."""
        self.storage = storage
        logger.info("UserManager привязан к персистентному storage")

    def load_monitors_from_storage(self) -> int:
        """Загружает активные мониторинги из storage в память.
        Возвращает количество загруженных записей.
        """
        if not self.storage:
            return 0
        try:
            data = self.storage.load_all()
            self.active_monitors.clear()
            self.active_monitors.update(data)
            logger.info(f"Загружено мониторингов из storage: {len(data)}")
            return len(data)
        except Exception as e:
            logger.error(f"Ошибка загрузки мониторингов из storage: {e}")
            return 0

    def save_all_to_storage(self) -> None:
        """Сохраняет все текущие мониторинги в storage (массово)."""
        if not self.storage:
            return
        try:
            self.storage.save_all(self.active_monitors)
        except Exception as e:
            logger.error(f"Ошибка массового сохранения мониторингов в storage: {e}")
    

# Создаем глобальный экземпляр менеджера пользователей без внешних зависимостей
user_manager = UserManager()
