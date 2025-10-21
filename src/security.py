#!/usr/bin/env python3
"""
Модуль безопасности для бота
"""

import re
import html
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SecurityValidator:
    """Класс для валидации и санитизации пользовательского ввода"""
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """
        Валидация номера телефона
        
        Args:
            phone: Номер телефона для проверки
            
        Returns:
            bool: True если номер корректный
        """
        if not phone or not isinstance(phone, str):
            return False
        
        # Удаляем пробелы и специальные символы
        clean_phone = re.sub(r'[^\d+]', '', phone.strip())
        
        # Проверяем формат белорусского номера
        belarus_patterns = [
            r'^\+375\d{9}$',  # +375XXXXXXXXX
            r'^375\d{9}$',    # 375XXXXXXXXX
            r'^\d{9}$',       # XXXXXXXXX (без кода страны)
        ]
        
        for pattern in belarus_patterns:
            if re.match(pattern, clean_phone):
                return True
        
        return False
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """
        Санитизация пользовательского ввода
        
        Args:
            text: Текст для санитизации
            max_length: Максимальная длина текста
            
        Returns:
            str: Очищенный текст
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Обрезаем по длине
        text = text[:max_length]
        
        # Экранируем HTML символы
        text = html.escape(text)
        
        # Удаляем потенциально опасные символы
        text = re.sub(r'[<>"\']', '', text)
        
        return text.strip()
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """
        Валидация формата даты
        
        Args:
            date_str: Дата в формате YYYY-MM-DD
            
        Returns:
            bool: True если дата корректная
        """
        if not date_str or not isinstance(date_str, str):
            return False
        
        # Проверяем формат даты
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        try:
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_time_range(time_range: str) -> bool:
        """
        Валидация временного диапазона
        
        Args:
            time_range: Диапазон времени в формате HH:MM-HH:MM
            
        Returns:
            bool: True если диапазон корректный
        """
        normalized = SecurityValidator.normalize_time_range(time_range)
        return normalized is not None

    @staticmethod
    def normalize_time_range(time_range: str) -> Optional[str]:
        """
        Нормализация и валидация пользовательского диапазона времени.
        Возвращает строку формата HH:MM-HH:MM либо None, если диапазон некорректный.
        """
        if not time_range or not isinstance(time_range, str):
            return None

        cleaned = time_range.strip()
        cleaned = cleaned.replace('–', '-').replace('—', '-').replace('−', '-')
        cleaned = re.sub(r'\s+', '', cleaned)

        match = re.match(r'^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$', cleaned)
        if not match:
            return None

        start_hour, start_min, end_hour, end_min = map(int, match.groups())

        if not (0 <= start_hour <= 23 and 0 <= start_min <= 59):
            return None
        if not (0 <= end_hour <= 23 and 0 <= end_min <= 59):
            return None

        if start_hour == end_hour and start_min == end_min:
            return None

        return f"{start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}"
    
    @staticmethod
    def sanitize_callback_data(data: str) -> str:
        """
        Санитизация callback data для кнопок
        
        Args:
            data: Данные для callback
            
        Returns:
            str: Очищенные данные
        """
        if not data or not isinstance(data, str):
            return ""
        
        # Только разрешенные символы для callback data
        sanitized = re.sub(r'[^a-zA-Z0-9_\-:]', '', data)
        
        # Ограничиваем длину (Telegram лимит 64 байта)
        return sanitized[:60]
    
    @staticmethod
    def log_security_event(event_type: str, user_id: int, details: dict):
        """
        Логирование событий безопасности
        
        Args:
            event_type: Тип события
            user_id: ID пользователя
            details: Детали события
        """
        logger.warning(
            f"🔒 SECURITY EVENT: {event_type} | User: {user_id} | Details: {details}"
        )

# Глобальный экземпляр валидатора
security = SecurityValidator()
