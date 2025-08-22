#!/usr/bin/env python3
"""
Диагностический скрипт для проверки всех компонентов проекта
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def check_environment():
    """Проверка переменных окружения"""
    print("🔧 Проверка переменных окружения:")
    
    # Проверяем обязательные переменные
    required_vars = {
        'TELEGRAM_BOT_TOKEN': 'Токен Telegram бота',
        'ADMIN_TELEGRAM_ID': 'ID администратора (опционально)'
    }
    
    missing = []
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            masked_value = value[:5] + "..." if len(value) > 5 else "***"
            print(f"  ✅ {var}: {masked_value} ({desc})")
        else:
            print(f"  ❌ {var}: НЕ УСТАНОВЛЕНА ({desc})")
            missing.append(var)
    
    return len(missing) == 0

def check_imports():
    """Проверка всех критических импортов"""
    print("\n📦 Проверка импортов:")
    
    imports_to_test = [
        ('telegram', 'python-telegram-bot'),
        ('requests', 'requests'),
        ('bs4', 'beautifulsoup4'),
        ('lxml', 'lxml'),
        ('dotenv', 'python-dotenv'),
        ('apscheduler', 'APScheduler'),
        ('aiohttp', 'aiohttp'),
        ('playwright', 'playwright'),
        ('psutil', 'psutil')
    ]
    
    failed = []
    for module, package in imports_to_test:
        try:
            __import__(module)
            print(f"  ✅ {module} ({package})")
        except ImportError as e:
            print(f"  ❌ {module} ({package}): {e}")
            failed.append(package)
    
    return len(failed) == 0

def check_project_structure():
    """Проверка структуры проекта"""
    print("\n📁 Проверка структуры проекта:")
    
    required_files = [
        'main.py',
        'Procfile', 
        'requirements.txt',
        'src/bot.py',
        'src/__init__.py',
        'src/auth/__init__.py',
        'src/utils/__init__.py',
        'src/monitoring/__init__.py',
        'src/database/__init__.py'
    ]
    
    missing = []
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}: НЕ НАЙДЕН")
            missing.append(file_path)
    
    return len(missing) == 0

def check_module_imports():
    """Проверка импорта собственных модулей"""
    print("\n🔍 Проверка собственных модулей:")
    
    modules_to_test = [
        ('bot', 'Основной модуль бота'),
        ('auth', 'Модули авторизации'),
        ('utils', 'Утилиты'),
        ('monitoring', 'Мониторинг'),
        ('database', 'База данных'),
        ('admin_panel', 'Админ панель'),
        ('security', 'Безопасность')
    ]
    
    failed = []
    for module, desc in modules_to_test:
        try:
            __import__(module)
            print(f"  ✅ {module} ({desc})")
        except ImportError as e:
            print(f"  ❌ {module} ({desc}): {e}")
            failed.append(module)
    
    return len(failed) == 0

def check_specific_functions():
    """Проверка конкретных функций и классов"""
    print("\n⚙️ Проверка конкретных компонентов:")
    
    try:
        from bot import main as bot_main
        print("  ✅ bot.main() функция найдена")
    except Exception as e:
        print(f"  ❌ bot.main(): {e}")
        return False
    
    try:
        from utils import FinalMarshrutochkaParser
        print("  ✅ FinalMarshrutochkaParser найден")
    except Exception as e:
        print(f"  ❌ FinalMarshrutochkaParser: {e}")
    
    try:
        from auth import bot_auth_manager
        print("  ✅ bot_auth_manager найден")
    except Exception as e:
        print(f"  ❌ bot_auth_manager: {e}")
    
    try:
        from monitoring import crash_handler
        print("  ✅ crash_handler найден")
    except Exception as e:
        print(f"  ❌ crash_handler: {e}")
    
    return True

def main():
    """Главная функция диагностики"""
    print("🚌 Диагностика проекта MarhrutochkaTG")
    print("=" * 50)
    
    # Загружаем .env файл
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env файл загружен")
    except Exception as e:
        print(f"⚠️ Проблема с .env: {e}")
    
    # Проверяем все компоненты
    checks = [
        ("Переменные окружения", check_environment),
        ("Внешние пакеты", check_imports), 
        ("Структура проекта", check_project_structure),
        ("Собственные модули", check_module_imports),
        ("Специфичные компоненты", check_specific_functions)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Ошибка при проверке {name}: {e}")
            results.append((name, False))
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ:")
    
    all_good = True
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
        if not result:
            all_good = False
    
    if all_good:
        print("\n🎉 Все проверки пройдены! Проект готов к запуску.")
    else:
        print("\n⚠️ Обнаружены проблемы. Необходимо их исправить.")
        print("\n💡 Рекомендации:")
        print("  1. Установите недостающие пакеты: pip install -r requirements.txt")
        print("  2. Проверьте файл .env с переменными окружения")
        print("  3. Убедитесь, что все файлы на месте")
    
    return all_good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
