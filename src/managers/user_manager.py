#!/usr/bin/env python3
"""
Модуль для управления пользователями и их данными
Использует современные практики python-telegram-bot без внешней БД
"""
import logging
from typing import Dict, Optional, Any
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
    
    def get_user_temp_data(self, user_id: int) -> dict:
        """Получает временные данные пользователя из локального хранилища"""
        return self.user_data_store.get(user_id, {})
    
    def set_user_temp_data(self, user_id: int, data: dict):
        """Устанавливает временные данные пользователя в локальное хранилище"""
        if user_id not in self.user_data_store:
            self.user_data_store[user_id] = {}
        self.user_data_store[user_id].update(data)
        logger.debug(f"Обновлены временные данные для пользователя {user_id}")
    
    def clear_user_temp_data(self, user_id: int):
        """Очищает временные данные пользователя из локального хранилища"""
        if self.user_data_store.pop(user_id, None):
            logger.debug(f"Очищены временные данные для пользователя {user_id}")
    
    def has_active_monitor(self, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя активный мониторинг"""
        return user_id in self.active_monitors
    
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
    
    def get_all_active_monitors(self) -> Dict[int, dict]:
        """Возвращает копию всех активных мониторингов"""
        return self.active_monitors.copy()
    
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику по пользователям и мониторингам"""
        return {
            'active_monitors_count': len(self.active_monitors),
            'temp_data_users_count': len(self.user_data_store),
            'active_monitors': list(self.active_monitors.keys()),
            'timestamp': datetime.now().isoformat()
        }
    
    def cleanup_inactive_data(self, max_age_hours: int = 24):
        """
        Очищает неактивные данные пользователей старше указанного времени.
        Помогает избежать утечек памяти при длительной работе.
        """
        current_time = datetime.now()
        cleanup_count = 0
        
        # Очищаем старые мониторинги
        expired_monitors = []
        for user_id, monitor in self.active_monitors.items():
            created_at = datetime.fromisoformat(monitor.get('created_at', current_time.isoformat()))
            age_hours = (current_time - created_at).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                expired_monitors.append(user_id)
        
        for user_id in expired_monitors:
            self.remove_user_monitor(user_id)
            cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Очищено {cleanup_count} неактивных мониторингов")
        
        return cleanup_count


# Создаем глобальный экземпляр менеджера пользователей без внешних зависимостей
user_manager = UserManager()
