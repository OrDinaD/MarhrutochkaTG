#!/usr/bin/env python3
"""
Тест для проверки исправлений Railway logger
"""

import logging
import sys

# Имитируем Railway logger без необходимых атрибутов
class FakeLogger:
    def __init__(self):
        self.logger = logging.getLogger('test')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        self.logger.addHandler(handler)
    
    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
    
    # НЕТ system_action, bot_action, admin_action методов!

# Создаем fake logger как в Railway
logger = FakeLogger()

# Проверяем наличие Railway-специфичных методов
is_railway_logger = hasattr(logger, 'system_action') and hasattr(logger, 'bot_action')
print(f"is_railway_logger: {is_railway_logger}")

# Создаем safe logging функции как в bot.py
def safe_log_system(message, data=None, level="info"):
    """Безопасное логирование системных событий"""
    if hasattr(logger, 'system_action'):
        logger.system_action(message, data or {}, level=level)
    else:
        log_func = getattr(logger, level, logger.info)
        if data:
            log_func(f"🔧 SYSTEM: {message} | Data: {data}")
        else:
            log_func(f"🔧 SYSTEM: {message}")

def safe_log_bot(message, data=None, level="info"):
    """Безопасное логирование действий бота"""
    if hasattr(logger, 'bot_action'):
        logger.bot_action(message, data or {}, level=level)
    else:
        log_func = getattr(logger, level, logger.info)
        if data:
            log_func(f"🤖 BOT: {message} | Data: {data}")
        else:
            log_func(f"🤖 BOT: {message}")

def safe_log_admin(message, data=None, level="info"):
    """Безопасное логирование админских действий"""
    if hasattr(logger, 'admin_action'):
        logger.admin_action(message, data or {}, level=level)
    else:
        log_func = getattr(logger, level, logger.info)
        if data:
            log_func(f"👑 ADMIN: {message} | Data: {data}")
        else:
            log_func(f"👑 ADMIN: {message}")

# Тестируем safe logging
print("\n=== Тестируем safe logging функции ===")
safe_log_system("Тест системного сообщения", {"test": "data"})
safe_log_bot("Тест бот сообщения", {"user_id": 123})
safe_log_admin("Тест админ сообщения", level="warning")

print("\n✅ Все safe logging функции работают корректно!")
