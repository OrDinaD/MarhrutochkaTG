#!/bin/bash

# 🚌 Скрипт запуска Telegram-бота мониторинга маршруточки

echo "🚀 Запуск бота мониторинга маршруточки"
echo "=============================================="

# Проверяем, что мы в правильной директории
if [ ! -f "main.py" ]; then
    echo "❌ Файл main.py не найден!"
    echo "💡 Запустите скрипт из корневой папки проекта"
    exit 1
fi

# Проверяем виртуальное окружение
if [ ! -d "venv" ]; then
    echo "📦 Создаю виртуальное окружение..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
echo "🔧 Активирую виртуальное окружение..."
source venv/bin/activate

# Устанавливаем/обновляем зависимости
echo "📚 Проверяю зависимости..."
pip install -r requirements.txt --quiet

# Проверяем .env файл
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "💡 Создайте файл .env с токеном TELEGRAM_BOT_TOKEN"
    exit 1
fi

# Проверяем токен
if ! grep -q "TELEGRAM_BOT_TOKEN=" .env; then
    echo "❌ Токен TELEGRAM_BOT_TOKEN не найден в .env!"
    exit 1
fi

echo "✅ Все готово к запуску!"
echo ""
echo "📱 Бот: @MarshrutochkaOst_bot"
echo "🔔 Мониторинг каждые 5 минут"
echo "⛔ Ctrl+C для остановки"
echo "=============================================="

# Запускаем бота
python main.py
