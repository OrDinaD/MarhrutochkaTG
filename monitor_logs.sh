#!/bin/bash

# Скрипт для мониторинга логов Railway

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

# Проверяем, привязан ли проект
railway status &> /dev/null
if [ $? -ne 0 ]; then
    read -p "Введите ID проекта Railway: " project_id
    railway link "$project_id"
fi

# Показываем последние логи
echo "📊 Последние логи вашего проекта:"
railway logs
