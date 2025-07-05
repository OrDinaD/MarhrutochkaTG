#!/bin/bash

# Скрипт для деплоя на Railway

# Проверяем наличие Railway CLI
if ! command -v railway &> /dev/null
then
    echo "🚨 Railway CLI не установлен!"
    echo "Устанавливаем Railway CLI..."
    npm i -g @railway/cli
fi

# Проверяем авторизацию в Railway
railway whoami &> /dev/null
if [ $? -ne 0 ]; then
    echo "🔑 Требуется авторизация в Railway"
    railway login
fi

# Спрашиваем пользователя о необходимости создать новый проект
read -p "Создать новый проект? (y/n): " create_new_project
if [ "$create_new_project" = "y" ]; then
    echo "🛤️ Создаем новый проект на Railway..."
    railway init
else
    read -p "Введите ID существующего проекта Railway: " project_id
    railway link "$project_id"
fi

# Спрашиваем пользователя о деталях деплоя
read -p "Введите токен Telegram бота: " telegram_token
read -p "Введите токен бота для логирования: " log_bot_token
read -p "Введите ID чата для логирования: " log_chat_id

# Настраиваем переменные окружения
echo "⚙️ Настраиваем переменные окружения..."
railway variables set TELEGRAM_BOT_TOKEN="$telegram_token"
railway variables set LOG_BOT_TOKEN="$log_bot_token"
railway variables set LOG_CHAT_ID="$log_chat_id"
railway variables set PYTHONUNBUFFERED=1
railway variables set TZ="Europe/Moscow"

# Выполняем деплой
echo "🚀 Выполняем деплой на Railway..."
railway up

# Получаем URL и другую информацию о деплое
echo "📊 Информация о деплое:"
railway status

echo "✅ Деплой успешно завершен!"
