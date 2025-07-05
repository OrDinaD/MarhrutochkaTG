#!/bin/bash

# Скрипт для управления ботом в Railway

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

show_menu() {
    clear
    echo "🤖 Управление ботом в Railway"
    echo "-----------------------------"
    echo "1. Просмотр логов в реальном времени"
    echo "2. Просмотр статуса деплоя"
    echo "3. Перезапуск бота"
    echo "4. Обновить переменные окружения"
    echo "5. Обновить код (новый деплой)"
    echo "0. Выход"
    echo "-----------------------------"
    read -p "Выберите действие: " choice
    
    case $choice in
        1)
            echo "📊 Логи в реальном времени (Ctrl+C для выхода):"
            railway logs -f
            read -p "Нажмите Enter для возврата в меню"
            show_menu
            ;;
        2)
            echo "📊 Статус деплоя:"
            railway status
            read -p "Нажмите Enter для возврата в меню"
            show_menu
            ;;
        3)
            echo "🔄 Перезапуск бота..."
            railway service restart
            echo "✅ Бот перезапущен!"
            read -p "Нажмите Enter для возврата в меню"
            show_menu
            ;;
        4)
            update_variables
            read -p "Нажмите Enter для возврата в меню"
            show_menu
            ;;
        5)
            echo "🚀 Обновление кода бота..."
            railway up
            echo "✅ Код бота обновлен!"
            read -p "Нажмите Enter для возврата в меню"
            show_menu
            ;;
        0)
            echo "👋 До свидания!"
            exit 0
            ;;
        *)
            echo "❌ Неверный выбор, попробуйте снова"
            read -p "Нажмите Enter для возврата в меню"
            show_menu
            ;;
    esac
}

update_variables() {
    echo "⚙️ Обновление переменных окружения"
    read -p "Введите токен Telegram бота [оставьте пустым для пропуска]: " telegram_token
    read -p "Введите токен бота для логирования [оставьте пустым для пропуска]: " log_bot_token
    read -p "Введите ID чата для логирования [оставьте пустым для пропуска]: " log_chat_id
    
    if [ ! -z "$telegram_token" ]; then
        railway variables set TELEGRAM_BOT_TOKEN="$telegram_token"
    fi
    
    if [ ! -z "$log_bot_token" ]; then
        railway variables set LOG_BOT_TOKEN="$log_bot_token"
    fi
    
    if [ ! -z "$log_chat_id" ]; then
        railway variables set LOG_CHAT_ID="$log_chat_id"
    fi
    
    echo "✅ Переменные окружения обновлены!"
}

# Запускаем главное меню
show_menu
