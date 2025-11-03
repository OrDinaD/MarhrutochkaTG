#!/usr/bin/env python3
"""
Скрипт для проверки подключения к Redis и просмотра активных мониторингов
"""
import os
import sys
import json

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage.monitoring_storage import create_storage_from_env


def main():
    print("🔍 Проверка Redis хранилища...")
    print()
    
    # Проверяем переменные окружения
    print("📋 Переменные окружения:")
    print(f"  MONITORING_STORAGE: {os.getenv('MONITORING_STORAGE', 'не установлена (по умолчанию file)')}")
    print(f"  REDIS_URL: {'установлена ✅' if os.getenv('REDIS_URL') else 'не установлена ❌'}")
    print(f"  RAILWAY_REDIS_URL: {'установлена ✅' if os.getenv('RAILWAY_REDIS_URL') else 'не установлена ❌'}")
    print()
    
    # Создаем storage
    try:
        storage = create_storage_from_env()
        storage_type = type(storage).__name__
        print(f"✅ Storage создан: {storage_type}")
        print()
    except Exception as e:
        print(f"❌ Ошибка создания storage: {e}")
        return 1
    
    # Проверяем подключение
    try:
        if hasattr(storage, 'ping'):
            is_alive = storage.ping()
            print(f"🏓 Ping: {'✅ OK' if is_alive else '❌ FAILED'}")
        else:
            print("🏓 Ping: не поддерживается для этого типа storage")
    except Exception as e:
        print(f"❌ Ошибка ping: {e}")
        return 1
    
    print()
    
    # Загружаем все мониторинги
    try:
        monitors = storage.load_all()
        print(f"📊 Найдено мониторингов: {len(monitors)}")
        print()
        
        if monitors:
            print("📝 Активные мониторинги:")
            for user_id, config in monitors.items():
                print(f"\n  👤 User ID: {user_id}")
                print(f"     Направление: {config.get('direction', 'не указано')}")
                print(f"     Дата: {config.get('date', 'не указана')}")
                print(f"     Время: {config.get('time_range', 'не указано')}")
                print(f"     Создан: {config.get('created_at', 'неизвестно')}")
        else:
            print("ℹ️  Активных мониторингов не найдено")
            
    except Exception as e:
        print(f"❌ Ошибка загрузки мониторингов: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    print("✅ Проверка завершена")
    return 0


if __name__ == "__main__":
    sys.exit(main())
