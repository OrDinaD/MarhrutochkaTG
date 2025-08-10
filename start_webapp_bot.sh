#!/bin/bash

# Скрипт для запуска бота с WebApp функциями
# Требуются переменные окружения TELEGRAM_BOT_TOKEN и ADMIN_TELEGRAM_ID

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Запуск Telegram бота с WebApp функциями..."

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Устанавливаем зависимости
echo "📚 Проверка зависимостей..."
pip install -r requirements.txt

# Проверяем переменные окружения
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Ошибка: Переменная TELEGRAM_BOT_TOKEN не установлена!"
    echo "Установите её командой: export TELEGRAM_BOT_TOKEN='ваш_токен_бота'"
    exit 1
fi

if [ -z "$ADMIN_TELEGRAM_ID" ]; then
    echo "⚠️  Внимание: Переменная ADMIN_TELEGRAM_ID не установлена!"
    echo "Админ-панель будет недоступна. Установите её командой: export ADMIN_TELEGRAM_ID='ваш_id'"
fi

echo "✅ Все проверки пройдены. Запуск бота..."
python src/bot.py
