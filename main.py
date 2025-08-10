#!/usr/bin/env python3
"""
Главная точка входа для Telegram-бота MarhrutochkaTG
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем src в путь
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

def check_environment():
    """Проверка переменных окружения"""
    required_vars = ['TELEGRAM_BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Отсутствуют обязательные переменные окружения:")
        for var in missing_vars:
            print(f"   • {var}")
        print("\n💡 Создайте файл .env с необходимыми переменными")
        print("📝 Пример:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        print("ADMIN_TELEGRAM_ID=your_admin_id")
        return False
    
    return True

def main():
    """Главная функция"""
    print("🚌 MarhrutochkaTG Bot v2.0")
    print("=" * 40)
    
    # Проверяем окружение
    if not check_environment():
        sys.exit(1)
    
    print("✅ Переменные окружения проверены")
    
    # Импортируем и запускаем бота
    try:
        from bot import main as bot_main
        print("🚀 Запуск бота...")
        bot_main()
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Убедитесь, что все файлы находятся в папке src/")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Бот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
