#!/usr/bin/env python3
"""
Главный файл запуска Telegram-бота MarhrutochkaTG
"""

import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    from bot import main
    main()
