#!/usr/bin/env python3
"""
Модуль для управления пользователями и их данными
Использует современные практики python-telegram-bot без внешней БД
"""
import logging
from typing import Dict, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class UserManager:
    """
    Класс для управления пользователями и их данными.
    Использует локальное хранение данных в памяти для максимальной производительности.
    """
    
    def __init__(self):
        self.user_data_store = {}  # Локальное хранилище для временных данных
        self.active_monitors = {}  # Активные мониторинги
        
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
        
        logger.info(f"Установлен мониторинг для пользователя {user_id}")
    
    def remove_user_monitor(self, user_id: int) -> bool:
        """Удаляет мониторинг пользователя из локального хранилища"""
        if user_id in self.active_monitors:
            del self.active_monitors[user_id]
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
    

# Создаем глобальный экземпляр менеджера пользователей без внешних зависимостей
user_manager = UserManager()
