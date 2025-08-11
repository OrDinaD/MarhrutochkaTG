#!/usr/bin/env python3
"""
Расширенная система логирования для Railway с JSON форматированием
Интеграция с crash handler и автоматическим мониторингом
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import platform

class RailwayLoggerEnhanced:
    """Расширенный логгер для Railway с crash handling интеграцией"""
    
    def __init__(self, name: str = "MarshrutochkaTG"):
        self.name = name
        self.is_railway = bool(os.getenv('RAILWAY_SERVICE_NAME'))
        self.logs_dir = Path('logs')
        self.logs_dir.mkdir(exist_ok=True)
        
        # Настраиваем логгер
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Очищаем существующие handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Настройка обработчиков логов"""
        
        # Форматтер для Railway (JSON)
        railway_formatter = RailwayJSONFormatter()
        
        # Console handler для Railway (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(railway_formatter)
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)
        
        # File handler для локального хранения
        if not self.is_railway:  # Только для локальной разработки
            file_handler = logging.FileHandler(
                self.logs_dir / 'bot.log',
                encoding='utf-8'
            )
            file_handler.setFormatter(railway_formatter)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)
        
        # Error handler для критичных ошибок
        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setFormatter(railway_formatter)
        error_handler.setLevel(logging.ERROR)
        self.logger.addHandler(error_handler)
    
    def _get_context(self) -> Dict[str, Any]:
        """Получает контекст для логирования"""
        return {
            "timestamp": datetime.now().isoformat(),
            "service": "MarshrutochkaTG",
            "environment": "railway" if self.is_railway else "local",
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "process_id": os.getpid(),
            "railway_service": os.getenv('RAILWAY_SERVICE_NAME'),
            "railway_environment": os.getenv('RAILWAY_ENVIRONMENT_NAME'),
            "railway_project": os.getenv('RAILWAY_PROJECT_NAME')
        }
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Информационное логирование"""
        context = self._get_context()
        if extra:
            context.update(extra)
        
        self.logger.info(json.dumps({
            "level": "info",
            "message": message,
            **context,
            **kwargs
        }, ensure_ascii=False, default=str))
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Логирование ошибок"""
        context = self._get_context()
        if extra:
            context.update(extra)
        
        if exc_info:
            context["exception"] = {
                "type": sys.exc_info()[0].__name__ if sys.exc_info()[0] else None,
                "message": str(sys.exc_info()[1]) if sys.exc_info()[1] else None,
                "traceback": traceback.format_exc()
            }
        
        self.logger.error(json.dumps({
            "level": "error",
            "message": message,
            **context,
            **kwargs
        }, ensure_ascii=False, default=str))
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Логирование предупреждений"""
        context = self._get_context()
        if extra:
            context.update(extra)
        
        self.logger.warning(json.dumps({
            "level": "warning",
            "message": message,
            **context,
            **kwargs
        }, ensure_ascii=False, default=str))
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Отладочное логирование"""
        context = self._get_context()
        if extra:
            context.update(extra)
        
        self.logger.debug(json.dumps({
            "level": "debug",
            "message": message,
            **context,
            **kwargs
        }, ensure_ascii=False, default=str))
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Критичное логирование"""
        context = self._get_context()
        if extra:
            context.update(extra)
        
        self.logger.critical(json.dumps({
            "level": "critical",
            "message": message,
            **context,
            **kwargs
        }, ensure_ascii=False, default=str))
    
    # Специализированные методы для разных типов событий
    def bot_action(self, message: str, data: Optional[Dict[str, Any]] = None, level: str = "info"):
        """Логирование действий бота"""
        extra = {"category": "bot_action"}
        if data:
            extra.update(data)
        
        getattr(self, level)(f"🤖 {message}", extra=extra)
    
    def user_action(self, message: str, user_id: Optional[int] = None, data: Optional[Dict[str, Any]] = None, level: str = "info"):
        """Логирование действий пользователя"""
        extra = {"category": "user_action"}
        if user_id:
            extra["user_id"] = user_id
        if data:
            extra.update(data)
        
        getattr(self, level)(f"👤 {message}", extra=extra)
    
    def system_action(self, message: str, data: Optional[Dict[str, Any]] = None, level: str = "info"):
        """Логирование системных действий"""
        extra = {"category": "system_action"}
        if data:
            extra.update(data)
        
        getattr(self, level)(f"⚙️ {message}", extra=extra)
    
    def monitoring_action(self, message: str, data: Optional[Dict[str, Any]] = None, level: str = "info"):
        """Логирование мониторинга"""
        extra = {"category": "monitoring_action"}
        if data:
            extra.update(data)
        
        getattr(self, level)(f"🔍 {message}", extra=extra)
    
    def crash_event(self, message: str, crash_id: str, data: Optional[Dict[str, Any]] = None):
        """Логирование crash событий"""
        extra = {
            "category": "crash_event",
            "crash_id": crash_id,
            "severity": "critical"
        }
        if data:
            extra.update(data)
        
        self.critical(f"💥 {message}", extra=extra)
    
    def recovery_event(self, message: str, recovery_id: str, success: bool, data: Optional[Dict[str, Any]] = None):
        """Логирование recovery событий"""
        extra = {
            "category": "recovery_event",
            "recovery_id": recovery_id,
            "success": success
        }
        if data:
            extra.update(data)
        
        level = "info" if success else "error"
        icon = "🔧" if success else "⚠️"
        getattr(self, level)(f"{icon} {message}", extra=extra)
    
    def performance_metric(self, metric_name: str, value: float, unit: str = "", data: Optional[Dict[str, Any]] = None):
        """Логирование метрик производительности"""
        extra = {
            "category": "performance_metric",
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit
        }
        if data:
            extra.update(data)
        
        self.info(f"📊 Metric {metric_name}: {value}{unit}", extra=extra)

class RailwayJSONFormatter(logging.Formatter):
    """JSON форматтер для Railway логов"""
    
    def format(self, record):
        # Если сообщение уже в JSON формате, возвращаем как есть
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Базовая структура лога
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Добавляем exception информацию если есть
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Добавляем дополнительные поля
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False, default=str)

# Создаем глобальный экземпляр логгера
railway_logger = RailwayLoggerEnhanced()

def setup_logging(level=logging.INFO) -> RailwayLoggerEnhanced:
    """Функция для настройки логирования (совместимость с существующим кодом)"""
    railway_logger.logger.setLevel(level)
    return railway_logger

if __name__ == "__main__":
    # Тестирование логгера
    logger = RailwayLoggerEnhanced()
    
    logger.info("Тестирование Railway логгера")
    logger.bot_action("Бот запущен", {"version": "1.0.0"})
    logger.user_action("Пользователь подключился", user_id=123456)
    logger.system_action("Система инициализирована")
    logger.monitoring_action("Мониторинг запущен", {"routes": 5})
    logger.performance_metric("response_time", 0.15, "s", {"endpoint": "/start"})
    
    # Тест с ошибкой
    try:
        raise ValueError("Тестовая ошибка")
    except Exception:
        logger.error("Произошла ошибка", exc_info=True)
    
    # Тест crash event
    logger.crash_event("Тестовый краш", "crash_123", {"details": "test crash"})
    
    # Тест recovery event
    logger.recovery_event("Восстановление успешно", "recovery_456", True, {"actions": 3})
    
    print("✅ Тестирование логгера завершено")
