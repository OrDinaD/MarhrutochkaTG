"""
Модули мониторинга и обработки ошибок
"""

from .crash_handler import crash_handler
from .diagnostic_system import diagnostic_system
from .auto_recovery import auto_recovery

# Импортируем с заглушками для отсутствующих функций
try:
    from .log_manager import setup_logging
except ImportError:
    def setup_logging(level=None):
        import logging
        return logging.getLogger(__name__)

# Добавляем get_logger как заглушку
def get_logger(name=None):
    import logging
    return logging.getLogger(name or __name__)

from .railway_logger_enhanced import RailwayLoggerEnhanced

# Создаем экземпляр railway_logger для использования в bot.py
railway_logger = None
try:
    railway_logger = RailwayLoggerEnhanced().logger
except Exception:
    railway_logger = None

__all__ = [
    'crash_handler',
    'diagnostic_system',
    'auto_recovery', 
    'setup_logging',
    'get_logger',
    'RailwayLoggerEnhanced',
    'railway_logger'
]
