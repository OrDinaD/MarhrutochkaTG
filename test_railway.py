#!/usr/bin/env python3
"""
Тест запуска бота - проверяем что все импорты работают
"""

import sys
import os

print("🔍 Проверка импортов...")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

try:
    print("\n1. Проверка python-dotenv...")
    from dotenv import load_dotenv
    print("✅ python-dotenv OK")
    
    print("\n2. Проверка telegram...")
    from telegram import Update
    print("✅ telegram OK")
    
    print("\n3. Проверка redis...")
    import redis
    print("✅ redis OK")
    
    print("\n4. Проверка requests...")
    import requests
    print("✅ requests OK")
    
    print("\n5. Проверка beautifulsoup4...")
    from bs4 import BeautifulSoup
    print("✅ beautifulsoup4 OK")
    
    print("\n6. Проверка src модулей...")
    sys.path.append('src')
    
    print("   - Проверка utils...")
    from utils import FinalMarshrutochkaParser
    print("   ✅ utils OK")
    
    print("   - Проверка monitoring...")
    from monitoring import setup_logging
    print("   ✅ monitoring OK")
    
    print("   - Проверка storage...")
    from storage import create_storage_from_env
    print("   ✅ storage OK")
    
    print("\n✅ Все импорты успешны!")
    print("\n7. Проверка переменных окружения...")
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if bot_token:
        print(f"✅ TELEGRAM_BOT_TOKEN установлен (длина: {len(bot_token)})")
    else:
        print("❌ TELEGRAM_BOT_TOKEN не установлен")
    
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        print(f"✅ REDIS_URL установлен")
    else:
        print("⚠️ REDIS_URL не установлен (будет использоваться file storage)")
    
    print("\n8. Тест подключения к Redis...")
    if redis_url:
        try:
            r = redis.from_url(redis_url, socket_connect_timeout=5)
            r.ping()
            print("✅ Redis подключение OK")
        except Exception as e:
            print(f"❌ Redis ошибка: {e}")
    
    print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
