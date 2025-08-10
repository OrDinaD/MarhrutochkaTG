#!/usr/bin/env python3
"""
Оптимизированная система логирования для Railway
Использует структурированное JSON логирование для красивого отображения в Railway
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from functools import wraps

class RailwayJSONFormatter(logging.Formatter):
    """
    Кастомный JSON форматтер для Railway
    Создает структурированные логи которые красиво отображаются в Railway console
    """
    
    def __init__(self):
        super().__init__()
        # Получаем информацию о Railway окружении
        self.replica_id = os.getenv('RAILWAY_REPLICA_ID', 'local')
        self.service_name = os.getenv('RAILWAY_SERVICE_NAME', 'unknown')
        self.region = os.getenv('RAILWAY_REPLICA_REGION', 'unknown')
        
    def format(self, record):
        """Форматирует логи в JSON для Railway"""
        
        # Создаем базовую структуру лога
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
            "service": self.service_name,
            "replica_id": self.replica_id,
            "region": self.region
        }
        
        # Добавляем информацию об исходном файле для debug логов
        if record.levelno <= logging.DEBUG:
            log_obj["source"] = {
                "file": getattr(record, 'pathname', ''),
                "line": getattr(record, 'lineno', 0),
                "function": getattr(record, 'funcName', None)
            }
        
        # Добавляем дополнительные поля из extra
        if hasattr(record, '__dict__'):
            reserved_keys = {
                'name', 'msg', 'args', 'levelname', 'levelno', 
                'pathname', 'filename', 'module', 'lineno', 'funcName',
                'created', 'msecs', 'relativeCreated', 'thread', 
                'threadName', 'processName', 'process', 'getMessage',
                'exc_info', 'exc_text', 'stack_info', 'extra'
            }
            
            for key, value in record.__dict__.items():
                if key not in reserved_keys:
                    log_obj[key] = value
        
        # Добавляем информацию об исключении
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj, ensure_ascii=False, default=str)

class RailwayStreamHandler(logging.StreamHandler):
    """
    Кастомный хэндлер для Railway который правильно маршрутизирует логи
    """
    
    def __init__(self):
        super().__init__()
        
    def emit(self, record):
        """Эмитирует лог в правильный поток для Railway"""
        try:
            msg = self.format(record)
            
            # Railway показывает INFO+ как зеленые (stdout), DEBUG как серые (stderr)
            if record.levelno >= logging.INFO:
                # INFO, WARNING, ERROR, CRITICAL идут в stdout (зеленые в Railway)
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
            else:
                # DEBUG идет в stderr (серые в Railway)
                sys.stderr.write(msg + '\n')
                sys.stderr.flush()
                
        except Exception:
            self.handleError(record)

class RailwayLogger:
    """
    Главный класс логгера оптимизированного для Railway
    """
    
    def __init__(self, name: str = "RailwayBot"):
        self.name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
        
        # Удаляем существующие хэндлеры
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
            
        # Настраиваем Railway хэндлер
        handler = RailwayStreamHandler()
        handler.setFormatter(RailwayJSONFormatter())
        self._logger.addHandler(handler)
        
        # Предотвращаем дублирование логов
        self._logger.propagate = False
        
        # Уровень логирования из переменной окружения
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        if hasattr(logging, log_level):
            self._logger.setLevel(getattr(logging, log_level))
    
    def _log(self, level: int, message: str, exc_info=None, **kwargs):
        """Внутренний метод для логирования"""
        self._logger.log(level, message, exc_info=exc_info, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Логирование debug сообщений"""
        self._log(logging.DEBUG, message, **kwargs)
        
    def info(self, message: str, **kwargs):
        """Логирование информационных сообщений"""
        self._log(logging.INFO, message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        """Логирование предупреждений"""
        self._log(logging.WARNING, message, **kwargs)
        
    def error(self, message: str, exc_info=None, **kwargs):
        """Логирование ошибок"""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)
        
    def critical(self, message: str, **kwargs):
        """Логирование критических ошибок"""
        self._log(logging.CRITICAL, message, **kwargs)
        
    def success(self, message: str, **kwargs):
        """Логирование успешных операций (как INFO но с меткой)"""
        kwargs['action'] = 'success'
        self._log(logging.INFO, f"✅ {message}", **kwargs)
        
    def bot_action(self, message: str, data: Optional[Dict] = None, level: str = "info", **kwargs):
        """Логирование действий бота"""
        if data:
            kwargs['user_id'] = data
        kwargs['action'] = 'bot_action'
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        self._log(log_level, f"🤖 {message}", **kwargs)
        
    def parser_action(self, message: str, data: Optional[Dict] = None, level: str = "info", **kwargs):
        """Логирование действий парсера"""
        if data:
            for key, value in data.items():
                kwargs[key] = data
        kwargs['action'] = 'parser'
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        self._log(log_level, f"🔍 {message}", **kwargs)
        
    def auth_action(self, message: str, data: Optional[Dict] = None, level: str = "info", **kwargs):
        """Логирование действий аутентификации"""
        if data:
            kwargs['user_id'] = data
        kwargs['action'] = 'auth'
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        self._log(log_level, f"🔐 {message}", **kwargs)
        
    def admin_action(self, message: str, data: Optional[Dict] = None, level: str = "info", **kwargs):
        """Логирование действий администратора"""
        if data:
            kwargs['user_id'] = data
        kwargs['action'] = 'admin'
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        self._log(log_level, f"👤 {message}", **kwargs)
        
    def measure_time(self, operation_name: str):
        """Декоратор для измерения времени выполнения функций"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self.info(f"⏱️ {operation_name} завершена", extra={
                        'operation': operation_name,
                        'execution_time': round(execution_time, 3),
                        'status': 'success'
                    })
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.error(f"⏱️ {operation_name} завершена с ошибкой", extra={
                        'operation': operation_name,
                        'execution_time': round(execution_time, 3),
                        'status': 'error',
                        'error': str(e)
                    })
                    raise
            return wrapper
        return decorator
        
    def time_context(self, operation_name: str):
        """Контекстный менеджер для измерения времени"""
        return TimeContext(self, operation_name)

class TimeContext:
    """Контекстный менеджер для измерения времени выполнения"""
    
    def __init__(self, logger: RailwayLogger, operation_name: str):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"⏱️ Начало операции: {self.operation_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"⏱️ {self.operation_name} завершена", extra={
                'operation': self.operation_name,
                'execution_time': round(execution_time, 3),
                'status': 'success'
            })
        else:
            self.logger.error(f"⏱️ {self.operation_name} завершена с ошибкой", extra={
                'operation': self.operation_name,
                'execution_time': round(execution_time, 3),
                'status': 'error',
                'error': str(exc_val)
            })

# Глобальный экземпляр для удобства использования
railway_logger = RailwayLogger("MarhrutochkaTG")

# Удобные функции для быстрого логирования
def log_info(message: str, **kwargs):
    """Быстрое логирование INFO"""
    railway_logger.info(message, **kwargs)

def log_warning(message: str, **kwargs):
    """Быстрое логирование WARNING"""
    railway_logger.warning(message, **kwargs)

def log_error(message: str, **kwargs):
    """Быстрое логирование ERROR"""
    railway_logger.error(message, **kwargs)

def log_debug(message: str, **kwargs):
    """Быстрое логирование DEBUG"""
    railway_logger.debug(message, **kwargs)

def log_startup(app_name: str, **kwargs):
    """Логирование запуска приложения"""
    railway_logger.success(f"🚀 {app_name} запущен", **kwargs)

def log_user_action(user_id: int, action: str, **kwargs):
    """Логирование действий пользователя"""
    kwargs['user_id'] = user_id
    kwargs['action'] = action
    railway_logger.info(f"👤 Пользователь {user_id}: {action}", **kwargs)

def log_success(message: str, **kwargs):
    """Быстрое логирование успешных операций"""
    railway_logger.success(message, **kwargs)

def bot_action(message: str, data: Optional[Dict] = None, **kwargs):
    """Быстрое логирование bot action"""
    railway_logger.bot_action(message, data=data, **kwargs)

def parser_action(message: str, data: Optional[Dict] = None, **kwargs):
    """Быстрое логирование parser action"""
    railway_logger.parser_action(message, data=data, **kwargs)

def auth_action(message: str, data: Optional[Dict] = None, **kwargs):
    """Быстрое логирование auth action"""
    railway_logger.auth_action(message, data=data, **kwargs)

def admin_action(message: str, data: Optional[Dict] = None, **kwargs):
    """Быстрое логирование admin action"""
    railway_logger.admin_action(message, data=data, **kwargs)

# Функции для измерения времени выполнения
def measure_time(operation_name: str):
    """Декоратор для измерения времени выполнения"""
    return railway_logger.measure_time(operation_name)

def time_context(operation_name: str):
    """Контекстный менеджер для измерения времени"""
    return railway_logger.time_context(operation_name)

if __name__ == "__main__":
    # Демонстрация использования
    logger = RailwayLogger("TestApp")
    
    logger.info("Тестовое сообщение")
    logger.bot_action("Пользователь подключился", {"user_id": 123})
    logger.error("Тестовая ошибка", extra={"error_code": "TEST_001"})
    
    @logger.measure_time("test_operation")
    def test_func():
        time.sleep(0.1)
        return "готово"
    
    result = test_func()
    print(f"Результат: {result}")
