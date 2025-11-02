#!/usr/bin/env python3
"""
Устойчивое хранилище активных мониторингов пользователей.
Поддерживаются два режима:
- Redis (предпочтительно для Railway) — через REDIS_URL/RAILWAY_REDIS_URL
- Файл JSON (fallback и для тестов) — через MONITORS_FILE_PATH

Выбор через MONITORING_STORAGE: "redis" или "file" (по умолчанию "file").
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional


class MonitoringStorage(ABC):
    """Абстракция для хранения активных мониторингов."""

    @abstractmethod
    def save_monitor(self, user_id: int, config: dict) -> None:
        ...

    @abstractmethod
    def delete_monitor(self, user_id: int) -> None:
        ...

    @abstractmethod
    def load_all(self) -> Dict[int, dict]:
        ...

    def save_all(self, monitors: Dict[int, dict]) -> None:
        """Опционально: массовое сохранение (по умолчанию итерация)."""
        for uid, cfg in monitors.items():
            self.save_monitor(uid, cfg)

    def ping(self) -> bool:
        """Проверка доступности (по умолчанию True)."""
        return True


class FileMonitoringStorage(MonitoringStorage):
    """JSON-файл как хранилище (надёжно для тестов/локально)."""

    def __init__(self, file_path: Optional[str] = None):
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        default_path = base_dir / "data" / "monitors.json"
        self.file_path = Path(file_path) if file_path else default_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> Dict[str, dict]:
        if not self.file_path.exists():
            return {}
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            # Поврежденный файл — начинаем с пустого
            return {}

    def _atomic_write(self, data: Dict[str, dict]) -> None:
        tmp_path = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(self.file_path)

    def save_monitor(self, user_id: int, config: dict) -> None:
        data = self._read()
        data[str(user_id)] = config
        self._atomic_write(data)

    def delete_monitor(self, user_id: int) -> None:
        data = self._read()
        if str(user_id) in data:
            data.pop(str(user_id), None)
            self._atomic_write(data)

    def load_all(self) -> Dict[int, dict]:
        data = self._read()
        # Приводим ключи к int
        return {int(k): v for k, v in data.items()}


class RedisMonitoringStorage(MonitoringStorage):
    """Хранилище в Redis. Хранит словари конфигов по ключу-хэшу."""

    KEY = "marhrutochka:active_monitors"  # Redis Hash: field=user_id(str), value=json

    def __init__(self, url: str):
        # Ленивая инициализация клиента, чтобы не падать в тестах без Redis
        import redis

        self._redis = redis.from_url(url, decode_responses=True, health_check_interval=10)

    def save_monitor(self, user_id: int, config: dict) -> None:
        self._redis.hset(self.KEY, str(user_id), json.dumps(config, ensure_ascii=False))

    def delete_monitor(self, user_id: int) -> None:
        self._redis.hdel(self.KEY, str(user_id))

    def load_all(self) -> Dict[int, dict]:
        raw = self._redis.hgetall(self.KEY) or {}
        result: Dict[int, dict] = {}
        for k, v in raw.items():
            try:
                result[int(k)] = json.loads(v)
            except Exception:
                continue
        return result

    def save_all(self, monitors: Dict[int, dict]) -> None:
        if not monitors:
            return
        payload = {str(k): json.dumps(v, ensure_ascii=False) for k, v in monitors.items()}
        # MSET для hash — HMSET через hset(name, mapping=...)
        self._redis.hset(self.KEY, mapping=payload)

    def ping(self) -> bool:
        try:
            return bool(self._redis.ping())
        except Exception:
            return False


def create_storage_from_env() -> MonitoringStorage:
    """Фабрика по переменным окружения."""
    mode = (os.getenv("MONITORING_STORAGE") or "file").strip().lower()
    if mode == "redis":
        url = (
            os.getenv("REDIS_URL")
            or os.getenv("RAILWAY_REDIS_URL")
            or os.getenv("UPSTASH_REDIS_REST_URL")  # на случай другого провайдера
        )
        if not url:
            # Фоллбэк на файл, чтобы приложение не падало
            return FileMonitoringStorage(os.getenv("MONITORS_FILE_PATH"))
        return RedisMonitoringStorage(url)

    # file (по умолчанию)
    return FileMonitoringStorage(os.getenv("MONITORS_FILE_PATH"))
