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
    # Безопасное создание директории перед инициализацией
    import os
    from pathlib import Path
    logs_dir = Path('data/logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    railway_logger = RailwayLoggerEnhanced().logger
except Exception as e:
    import logging
    logging.warning(f"Failed to initialize RailwayLoggerEnhanced: {e}")
    railway_logger = logging.getLogger("MarshrutochkaTG")

# Импортируем систему мониторинга маршрутов
from .route_monitoring import (
    RouteMonitoringSystem,
    RouteMonitoringError,
    RouteMonitoringValidator,
    route_monitoring_system,
    check_routes_for_user_job,
    monitoring_logger
)

__all__ = [
    'crash_handler',
    'diagnostic_system',
    'auto_recovery', 
    'setup_logging',
    'get_logger',
    'RailwayLoggerEnhanced',
    'railway_logger',
    'RouteMonitoringSystem',
    'RouteMonitoringError',
    'RouteMonitoringValidator',
    'route_monitoring_system',
    'check_routes_for_user_job',
    'monitoring_logger'
]
