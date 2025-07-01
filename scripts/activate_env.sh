#!/bin/bash

# Скрипт для активации виртуального окружения
# Использование: source scripts/activate_env.sh

if [ ! -d "venv" ]; then
    echo "🔧 Создание виртуального окружения..."
    python3 -m venv venv
    echo "✅ Виртуальное окружение создано!"
fi

echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

if [ -f "requirements.txt" ]; then
    echo "📦 Установка зависимостей..."
    pip install -r requirements.txt
    echo "✅ Зависимости установлены!"
fi

echo "🎉 Окружение готово! Используйте 'python main.py' для запуска бота"
