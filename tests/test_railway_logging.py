#!/usr/bin/env python3
"""
Демонстрационный скрипт для тестирования Railway-оптимизированного логирования
"""

import os
import sys
import time
from datetime import datetime

# Добавляем src в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.monitoring.railway_logger_enhanced import RailwayLoggerEnhanced

def test_railway_logging():
    """Тестирование всех возможностей Railway logger"""
    
    print("🧪 Тестирование Railway Logger...")
    print("=" * 50)
    
    # Создаем логгер
    logger = RailwayLoggerEnhanced("TestBot")
    
    # 1. Тестируем основные уровни логирования
    print("\n1️⃣ Основные уровни логирования:")
    logger.debug("Это debug сообщение (должно идти в stderr)")
    logger.info("Это info сообщение (должно идти в stdout)")
    logger.warning("Это warning сообщение (должно идти в stdout)")
    logger.error("Это error сообщение (должно идти в stdout)")
    
    # 2. Тестируем специализированные методы
    print("\n2️⃣ Специализированные методы:")
    
    logger.bot_action("Пользователь подключился", {
        "user_id": 12345,
        "username": "test_user",
        "timestamp": datetime.now().isoformat()
    })
    
    logger.auth_action("Успешная авторизация", {
        "user_id": 12345,
        "method": "telegram",
        "ip": "192.168.1.1"
    })
    
    logger.parser_action("Парсинг завершен", {
        "routes_found": 15,
        "processing_time": 2.5,
        "source": "marshrutochka.ru"
    })
    
    logger.admin_action("Пользователь заблокирован", {
        "admin_id": 99999,
        "target_user": 12345,
        "reason": "spam"
    })
    
    # 3. Тестируем измерение времени
    print("\n3️⃣ Измерение времени выполнения:")
    
    @logger.measure_time("test_operation")
    def slow_operation():
        time.sleep(1)
        return "Операция завершена"
    
    result = slow_operation()
    print(f"Результат: {result}")
    
    # 4. Тестируем контекстный менеджер
    print("\n4️⃣ Контекстный менеджер:")
    
    with logger.time_context("database_query"):
        time.sleep(0.5)
        logger.info("Выполняется запрос к базе данных...")
    
    # 5. Тестируем логирование ошибок
    print("\n5️⃣ Логирование ошибок:")
    
    try:
        raise ValueError("Тестовая ошибка для демонстрации")
    except Exception as e:
        logger.error("Произошла ошибка", exc_info=True, extra={
            "operation": "test_error",
            "error_type": type(e).__name__,
            "test_context": "demonstration"
        })
    
    # 6. Тестируем удобные функции
    print("\n6️⃣ Удобные функции:")
    
    from src.monitoring.railway_logger_enhanced import log_startup, log_user_action, log_error
    
    log_startup("TestApp", version="1.0.0", environment="test")
    log_user_action(12345, "button_click", button="start")
    log_error("Тестовая ошибка", operation="test_function", context="demonstration")
    
    print("\n✅ Тестирование завершено!")
    print("\nПроверьте логи:")
    print("- INFO, WARNING, ERROR должны отображаться зеленым в Railway")
    print("- DEBUG должен отображаться серым")
    print("- Все логи должны быть в JSON формате")
    print("- Время выполнения должно быть измерено")

if __name__ == "__main__":
    # Устанавливаем переменные окружения для имитации Railway
    os.environ.setdefault('RAILWAY_SERVICE_NAME', 'test-service')
    os.environ.setdefault('RAILWAY_REPLICA_ID', 'test-replica')
    os.environ.setdefault('RAILWAY_REPLICA_REGION', 'us-west1')
    os.environ.setdefault('LOG_LEVEL', 'DEBUG')
    
    test_railway_logging()
