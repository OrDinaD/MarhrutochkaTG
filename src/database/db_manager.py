#!/usr/bin/env python3
"""
Менеджер базы данных для постоянного хранения данных пользователей
"""

import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных для хранения данных пользователей"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Создаем папку data если её нет
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "marsha_bot.db"
        
        self.db_path = str(db_path)
        self.init_database()
        
    def init_database(self):
        """Инициализация базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        phone TEXT,
                        email TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_admin INTEGER DEFAULT 0,
                        profile_data TEXT  -- JSON с полными данными профиля
                    )
                ''')
                
                # Таблица сессий авторизации
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS auth_sessions (
                        user_id INTEGER PRIMARY KEY,
                        phone TEXT,
                        password_hash TEXT,
                        session_data TEXT,  -- JSON с данными сессии
                        last_login TIMESTAMP,
                        expires_at TIMESTAMP,
                        is_active INTEGER DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица мониторингов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS monitors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        monitor_config TEXT,  -- JSON с конфигурацией мониторинга
                        route_from TEXT,
                        route_to TEXT,
                        monitor_date TEXT,
                        is_active INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица бронирований
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bookings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        booking_id TEXT,
                        route TEXT,
                        booking_date TEXT,
                        departure_time TEXT,
                        ticket_number TEXT,
                        price TEXT,
                        status TEXT DEFAULT 'active',
                        booking_data TEXT,  -- JSON с полными данными бронирования
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица логов (опционально)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        action TEXT,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                conn.commit()
                logger.info(f"База данных инициализирована: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            
    def save_user(self, user_id: int, user_data: Dict) -> bool:
        """Сохраняет или обновляет данные пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли пользователь
                cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
                exists = cursor.fetchone()
                
                current_time = datetime.now().isoformat()
                profile_data_json = json.dumps(user_data.get('profile_data', {}), ensure_ascii=False)
                
                if exists:
                    # Обновляем существующего пользователя
                    cursor.execute('''
                        UPDATE users SET
                            username = ?,
                            first_name = ?,
                            last_name = ?,
                            phone = ?,
                            email = ?,
                            updated_at = ?,
                            profile_data = ?
                        WHERE user_id = ?
                    ''', (
                        user_data.get('username'),
                        user_data.get('first_name'),
                        user_data.get('last_name'),
                        user_data.get('phone'),
                        user_data.get('email'),
                        current_time,
                        profile_data_json,
                        user_id
                    ))
                else:
                    # Создаем нового пользователя
                    cursor.execute('''
                        INSERT INTO users (
                            user_id, username, first_name, last_name, 
                            phone, email, created_at, updated_at, profile_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        user_data.get('username'),
                        user_data.get('first_name'),
                        user_data.get('last_name'),
                        user_data.get('phone'),
                        user_data.get('email'),
                        current_time,
                        current_time,
                        profile_data_json
                    ))
                
                conn.commit()
                logger.info(f"Данные пользователя {user_id} сохранены")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка сохранения пользователя {user_id}: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получает данные пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, phone, email,
                           created_at, updated_at, is_admin, profile_data
                    FROM users WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    profile_data = {}
                    try:
                        if row[9]:  # profile_data
                            profile_data = json.loads(row[9])
                    except json.JSONDecodeError:
                        pass
                    
                    return {
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'last_name': row[3],
                        'phone': row[4],
                        'email': row[5],
                        'created_at': row[6],
                        'updated_at': row[7],
                        'is_admin': bool(row[8]),
                        'profile_data': profile_data
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {user_id}: {e}")
            return None
    
    def save_auth_session(self, user_id: int, phone: str, session_data: Dict) -> bool:
        """Сохраняет сессию авторизации"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                session_json = json.dumps(session_data, ensure_ascii=False)
                current_time = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO auth_sessions (
                        user_id, phone, session_data, last_login, is_active
                    ) VALUES (?, ?, ?, ?, 1)
                ''', (user_id, phone, session_json, current_time))
                
                conn.commit()
                logger.info(f"Сессия пользователя {user_id} сохранена")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка сохранения сессии {user_id}: {e}")
            return False
    
    def get_auth_session(self, user_id: int) -> Optional[Dict]:
        """Получает сессию авторизации"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT phone, session_data, last_login, is_active
                    FROM auth_sessions WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row and row[3]:  # is_active
                    session_data = {}
                    try:
                        if row[1]:  # session_data
                            session_data = json.loads(row[1])
                    except json.JSONDecodeError:
                        pass
                    
                    return {
                        'phone': row[0],
                        'session_data': session_data,
                        'last_login': row[2],
                        'is_active': bool(row[3])
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения сессии {user_id}: {e}")
            return None
    
    def save_monitor(self, user_id: int, monitor_config: Dict) -> bool:
        """Сохраняет конфигурацию мониторинга"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                config_json = json.dumps(monitor_config, ensure_ascii=False)
                current_time = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO monitors (
                        user_id, monitor_config, route_from, route_to, 
                        monitor_date, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    config_json,
                    monitor_config.get('from_location'),
                    monitor_config.get('to_location'),
                    monitor_config.get('date'),
                    current_time,
                    current_time
                ))
                
                conn.commit()
                logger.info(f"Мониторинг пользователя {user_id} сохранен")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка сохранения мониторинга {user_id}: {e}")
            return False
    
    def get_user_monitors(self, user_id: int) -> List[Dict]:
        """Получает активные мониторинги пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, monitor_config, route_from, route_to, 
                           monitor_date, created_at, updated_at
                    FROM monitors 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                monitors = []
                for row in cursor.fetchall():
                    monitor_config = {}
                    try:
                        if row[1]:  # monitor_config
                            monitor_config = json.loads(row[1])
                    except json.JSONDecodeError:
                        pass
                    
                    monitors.append({
                        'id': row[0],
                        'monitor_config': monitor_config,
                        'route_from': row[2],
                        'route_to': row[3],
                        'monitor_date': row[4],
                        'created_at': row[5],
                        'updated_at': row[6]
                    })
                
                return monitors
                
        except Exception as e:
            logger.error(f"Ошибка получения мониторингов {user_id}: {e}")
            return []
    
    def deactivate_monitor(self, monitor_id: int) -> bool:
        """Деактивирует мониторинг"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE monitors SET 
                        is_active = 0, 
                        updated_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), monitor_id))
                
                conn.commit()
                logger.info(f"Мониторинг {monitor_id} деактивирован")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка деактивации мониторинга {monitor_id}: {e}")
            return False
    
    def log_activity(self, user_id: int, action: str, details: str = "") -> bool:
        """Логирует активность пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO activity_logs (user_id, action, details)
                    VALUES (?, ?, ?)
                ''', (user_id, action, details))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка логирования активности {user_id}: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Очищает старые данные"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Удаляем старые логи
                cursor.execute('''
                    DELETE FROM activity_logs 
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(days_to_keep))
                
                # Деактивируем старые мониторинги
                cursor.execute('''
                    UPDATE monitors SET is_active = 0
                    WHERE created_at < datetime('now', '-{} days')
                    AND is_active = 1
                '''.format(days_to_keep))
                
                conn.commit()
                logger.info(f"Очистка старых данных завершена (сохранены последние {days_to_keep} дней)")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка очистки данных: {e}")
            return False


# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()
