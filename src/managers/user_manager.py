#!/usr/bin/env python3
"""
Модуль для управления пользователями и их данными
Объединяет функции работы с БД и пользовательскими данными
"""
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class UserManager:
    """Класс для управления пользователями и их данными"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.user_data_store = {}  # Локальное хранилище для временных данных
        self.active_monitors = {}  # Активные мониторинги
    
    def save_user_to_db(self, user_id: int, user_data: dict) -> bool:
        """Сохраняет данные пользователя в базу данных"""
        try:
            if self.db_manager:
                return self.db_manager.save_user(user_id, user_data)
            return False
        except Exception as e:
            logger.error(f"Ошибка сохранения пользователя {user_id}: {e}")
            return False

    def load_user_from_db(self, user_id: int) -> dict:
        """Загружает данные пользователя из базы данных"""
        try:
            if self.db_manager:
                return self.db_manager.get_user(user_id) or {}
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки пользователя {user_id}: {e}")
            return {}
    
    def save_user_monitor_to_db(self, user_id: int, monitor_config: dict) -> bool:
        """Сохраняет мониторинг пользователя в БД"""
        try:
            if self.db_manager and user_id in self.active_monitors:
                return self.db_manager.save_monitor(user_id, monitor_config)
            return False
        except Exception as e:
            logger.error(f"Ошибка сохранения мониторинга пользователя {user_id}: {e}")
            return False

    def load_user_monitors_from_db(self, user_id: int) -> list:
        """Загружает мониторинги пользователя из БД"""
        try:
            if self.db_manager:
                return self.db_manager.get_user_monitors(user_id)
            return []
        except Exception as e:
            logger.error(f"Ошибка загрузки мониторингов пользователя {user_id}: {e}")
            return []
    
    def get_user_temp_data(self, user_id: int) -> dict:
        """Получает временные данные пользователя"""
        return self.user_data_store.get(user_id, {})
    
    def set_user_temp_data(self, user_id: int, data: dict):
        """Устанавливает временные данные пользователя"""
        if user_id not in self.user_data_store:
            self.user_data_store[user_id] = {}
        self.user_data_store[user_id].update(data)
    
    def clear_user_temp_data(self, user_id: int):
        """Очищает временные данные пользователя"""
        self.user_data_store.pop(user_id, None)
    
    def has_active_monitor(self, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя активный мониторинг"""
        return user_id in self.active_monitors
    
    def get_user_monitor(self, user_id: int) -> Optional[dict]:
        """Получает конфигурацию мониторинга пользователя"""
        return self.active_monitors.get(user_id)
    
    def set_user_monitor(self, user_id: int, monitor_config: dict):
        """Устанавливает мониторинг для пользователя"""
        # Добавляем метаданные
        monitor_config['created_at'] = datetime.now().isoformat()
        monitor_config['user_id'] = user_id
        
        self.active_monitors[user_id] = monitor_config
        
        # Сохраняем в БД
        self.save_user_monitor_to_db(user_id, monitor_config)
        
        logger.info(f"Установлен мониторинг для пользователя {user_id}")
    
    def remove_user_monitor(self, user_id: int) -> bool:
        """Удаляет мониторинг пользователя"""
        if user_id in self.active_monitors:
            del self.active_monitors[user_id]
            
            # Удаляем из БД
            if self.db_manager:
                try:
                    self.db_manager.delete_monitor(user_id)
                except Exception as e:
                    logger.error(f"Ошибка удаления мониторинга из БД {user_id}: {e}")
            
            logger.info(f"Удален мониторинг пользователя {user_id}")
            return True
        return False
    
    def get_all_active_monitors(self) -> Dict[int, dict]:
        """Возвращает все активные мониторинги"""
        return self.active_monitors.copy()
    
    def load_all_monitors_from_db(self):
        """Загружает все мониторинги из БД при запуске"""
        if not self.db_manager:
            logger.warning("DB manager не инициализирован")
            return
        
        try:
            # Здесь можно добавить метод в db_manager для получения всех мониторингов
            logger.info("Мониторинги будут загружаться динамически из БД")
        except Exception as e:
            logger.error(f"Ошибка загрузки мониторингов из БД: {e}")
    
    def emergency_reset_user(self, user_id: int):
        """Экстренный сброс всех данных пользователя"""
        try:
            # Очищаем временные данные
            self.clear_user_temp_data(user_id)
            
            # Удаляем мониторинг
            self.remove_user_monitor(user_id)
            
            logger.warning(f"Выполнен экстренный сброс для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при экстренном сбросе пользователя {user_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику по пользователям"""
        return {
            'active_monitors_count': len(self.active_monitors),
            'temp_data_users_count': len(self.user_data_store),
            'active_monitors': list(self.active_monitors.keys()),
            'timestamp': datetime.now().isoformat()
        }


# Создаем глобальный экземпляр менеджера пользователей
user_manager = UserManager()
