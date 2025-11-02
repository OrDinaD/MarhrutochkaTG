#!/usr/bin/env python3
import importlib
import os
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_file_storage_persists_between_manager_restarts(tmp_path, monkeypatch):
    # Настраиваем file storage через ENV
    storage_file = tmp_path / "monitors.json"
    monkeypatch.setenv("MONITORING_STORAGE", "file")
    monkeypatch.setenv("MONITORS_FILE_PATH", str(storage_file))

    # Импортируем менеджер и storage фабрику
    user_manager_mod = importlib.import_module("src.managers.user_manager")
    storage_pkg = importlib.import_module("src.storage")

    # Привязываем storage и создаем мониторинг
    storage = storage_pkg.create_storage_from_env()
    user_manager_mod.user_manager.set_storage(storage)

    user_id = 777
    monitor = {
        "date": "2025-01-02",
        "direction": "minsk_ostrovets",
        "time_type": "departure",
        "time_range": "08:00-10:00",
        "chat_id": 12345,
    }
    user_manager_mod.user_manager.set_user_monitor(user_id, monitor)

    # Проверяем, что файл создан и содержит запись
    assert storage_file.exists()

    # Симулируем "перезапуск" менеджера — создаем новый объект и загружаем из storage
    fresh_manager = user_manager_mod.UserManager()
    fresh_manager.set_storage(storage)
    loaded = fresh_manager.load_monitors_from_storage()
    assert loaded == 1
    assert user_id in fresh_manager.active_monitors
    assert fresh_manager.active_monitors[user_id]["time_range"] == "08:00-10:00"
