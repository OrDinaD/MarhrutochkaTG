import pytest
import asyncio
import json
import os
import sys
from pathlib import Path
import importlib

# Add project root to sys.path
sys.path.append(str(Path(__file__).parents[1]))

@pytest.mark.asyncio
async def test_file_storage_persists_between_manager_restarts(tmp_path, monkeypatch):
    # Настраиваем file storage через ENV
    storage_file = tmp_path / "monitors.json"
    monkeypatch.setenv("MONITORING_STORAGE", "file")
    monkeypatch.setenv("MONITORS_FILE_PATH", str(storage_file))
    
    # Create initial empty file
    with open(storage_file, 'w') as f:
        json.dump({}, f)

    # Импортируем менеджер и storage фабрику
    # We need to reload modules to pick up env vars if they were already imported
    if 'src.managers.user_manager' in sys.modules:
        del sys.modules['src.managers.user_manager']
    if 'src.storage.monitoring_storage' in sys.modules:
        del sys.modules['src.storage.monitoring_storage']
    if 'src.storage' in sys.modules:
        del sys.modules['src.storage']
        
    import src.managers.user_manager as user_manager_mod
    import src.storage as storage_mod
    
    # 1. Create manager and storage
    manager1 = user_manager_mod.UserManager()
    storage1 = storage_mod.create_storage_from_env()
    manager1.set_storage(storage1)
    
    # Add monitor using the correct method
    user_id = 12345
    monitor_data = {
        "route_code": "AB123",
        "created_at": "2023-01-01",
        "is_active": True
    }
    
    manager1.set_user_monitor(user_id, monitor_data)
    
    # 2. Destroy manager1 (simulate restart)
    # Since saving might be async or sync, verify it's saved
    # The implementation of set_user_monitor calls storage.save_monitor
    
    del manager1
    
    # 3. Create manager2
    # Re-import to simulate fresh start
    if 'src.managers.user_manager' in sys.modules:
        del sys.modules['src.managers.user_manager']
    if 'src.storage' in sys.modules:
        del sys.modules['src.storage']

    import src.managers.user_manager as user_manager_mod2
    import src.storage as storage_mod2
        
    manager2 = user_manager_mod2.UserManager()
    storage2 = storage_mod2.create_storage_from_env()
    manager2.set_storage(storage2)
    
    # Load from storage
    loaded_count = manager2.load_monitors_from_storage()
    
    # 4. Verify monitor exists
    assert loaded_count == 1
    monitor = manager2.get_user_monitor(user_id)
    assert monitor is not None
    assert monitor["route_code"] == "AB123"