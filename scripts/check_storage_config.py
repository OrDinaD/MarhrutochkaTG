#!/usr/bin/env python3
"""
Быстрая проверка: используется ли Redis для мониторингов
"""
import os

print("🔍 Проверка настроек хранилища мониторингов\n")

# Проверяем MONITORING_STORAGE
storage_mode = os.getenv("MONITORING_STORAGE", "file").strip().lower()
print(f"📦 MONITORING_STORAGE: {storage_mode}")

# Проверяем Redis URL
redis_url = os.getenv("REDIS_URL") or os.getenv("RAILWAY_REDIS_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
has_redis = bool(redis_url)

print(f"🔗 Redis URL: {'✅ настроен' if has_redis else '❌ не настроен'}")
print()

# Выводим что используется
if storage_mode == "redis" and has_redis:
    print("✅ Используется Redis - мониторинги СОХРАНЯЮТСЯ при деплое")
    print(f"   URL: {redis_url[:30]}..." if redis_url else "")
elif storage_mode == "redis" and not has_redis:
    print("⚠️  MONITORING_STORAGE=redis, но REDIS_URL не настроен!")
    print("   Будет использован файл (данные ПОТЕРЯЮТСЯ при деплое)")
else:
    print("⚠️  Используется файловое хранилище - мониторинги ПОТЕРЯЮТСЯ при деплое")
    print("   Для Railway нужно добавить:")
    print("   1. Redis сервис в Railway dashboard")
    print("   2. Переменную MONITORING_STORAGE=redis")

print()
print("📖 Подробнее: docs/REDIS_SETUP.md")
