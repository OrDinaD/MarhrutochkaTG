#!/usr/bin/env python3
"""
Абстракции и реализации хранилищ для устойчивого сохранения состояния бота
"""

from .monitoring_storage import (
    MonitoringStorage,
    FileMonitoringStorage,
    RedisMonitoringStorage,
    create_storage_from_env,
)

__all__ = [
    "MonitoringStorage",
    "FileMonitoringStorage",
    "RedisMonitoringStorage",
    "create_storage_from_env",
]
