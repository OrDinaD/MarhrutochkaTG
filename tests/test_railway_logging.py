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
    
    logger.user_action("Успешная авторизация", user_id=12345, data={
        "method": "telegram",
        "ip": "192.168.1.1"
    })
    
    logger.system_action("Парсинг завершен", {
        "routes_found": 15,
        "processing_time": 2.5,
        "source": "marshrutochka.ru"
    })
    
    logger.monitoring_action("Пользователь заблокирован", {
        "admin_id": 99999,
        "target_user": 12345,
        "reason": "spam"
    })
    
    # 3. Тестируем базовые методы логирования
    print("\n3️⃣ Базовые методы логирования:")
    
    # Имитируем медленную операцию
    print("Выполняется медленная операция...")
    time.sleep(0.1)  # Короткая пауза для демонстрации
    logger.info("Операция завершена успешно")
    
    # 4. Тестируем логирование ошибок с дополнительной информацией
    print("\n4️⃣ Логирование ошибок:")
    
    try:
        raise ValueError("Тестовая ошибка для демонстрации")
    except Exception as e:
        logger.error("Произошла ошибка", exc_info=True, extra={
            "operation": "test_error",
            "error_type": type(e).__name__,
            "test_context": "demonstration"
        })
    
    print("\n✅ Тестирование завершено!")
    print("\nПроверьте логи:")
    print("- INFO, WARNING, ERROR должны отображаться зеленым в Railway")
    print("- DEBUG должен отображаться серым")
    print("- Все логи должны быть в JSON формате")

if __name__ == "__main__":
    # Устанавливаем переменные окружения для имитации Railway
    os.environ.setdefault('RAILWAY_SERVICE_NAME', 'test-service')
    os.environ.setdefault('RAILWAY_REPLICA_ID', 'test-replica')
    os.environ.setdefault('RAILWAY_REPLICA_REGION', 'us-west1')
    os.environ.setdefault('LOG_LEVEL', 'DEBUG')
    
    test_railway_logging()
