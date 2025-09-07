#!/bin/bash
# Railway Deployment Script для MarhrutochkaTG
# Автоматический деплой с мониторингом логов и crash handling

set -e  # Прекратить выполнение при любой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Railway Deployment Script для MarhrutochkaTG${NC}"
echo -e "${BLUE}===============================================${NC}"

# Проверяем наличие Railway CLI
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ Railway CLI не установлен!${NC}"
    echo -e "${YELLOW}💡 Установите: npm install -g @railway/cli${NC}"
    exit 1
fi

# Проверяем авторизацию в Railway
if ! railway whoami &> /dev/null; then
    echo -e "${RED}❌ Не авторизованы в Railway!${NC}"
    echo -e "${YELLOW}💡 Выполните: railway login${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Railway CLI готов к работе${NC}"

# Проверяем наличие requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo -e "${YELLOW}⚠️ requirements.txt не найден, создаем...${NC}"
    pip freeze > requirements.txt
    echo -e "${GREEN}✅ requirements.txt создан${NC}"
fi

# Создаем .railwayignore если его нет
if [ ! -f ".railwayignore" ]; then
    echo -e "${YELLOW}💡 Создаем .railwayignore...${NC}"
    cat > .railwayignore << 'EOF'
# Development files
.env
.venv/
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
.DS_Store
Thumbs.db

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Logs (will be created in container)
logs/*.log
crash_logs/*.json
user_sessions/*.json
backups/*
temp_recovery/*

# Test files
test_*.py
*_test.py
tests/

# Git
.git/
.gitignore

# Documentation
docs/
*.md
EOF
    echo -e "${GREEN}✅ .railwayignore создан${NC}"
fi

# Функция для проверки статуса деплоя
check_deployment_status() {
    local timeout=300  # 5 минут
    local counter=0
    local interval=10
    
    echo -e "${BLUE}🔍 Мониторинг статуса деплоя...${NC}"
    
    while [ $counter -lt $timeout ]; do
        # Получаем статус через railway CLI
        if railway logs --json > /tmp/railway_logs.json 2>/dev/null; then
            # Проверяем на успешный деплой
            if grep -q "Deployment successful\|Build successful\|Started" /tmp/railway_logs.json 2>/dev/null; then
                echo -e "${GREEN}✅ Деплой успешно завершен!${NC}"
                return 0
            fi
            
            # Проверяем на ошибки
            if grep -q "Failed\|Error\|Crash" /tmp/railway_logs.json 2>/dev/null; then
                echo -e "${RED}❌ Обнаружена ошибка в деплое!${NC}"
                return 1
            fi
        fi
        
        echo -e "${YELLOW}⏳ Ожидание завершения деплоя... (${counter}s/${timeout}s)${NC}"
        sleep $interval
        counter=$((counter + interval))
    done
    
    echo -e "${YELLOW}⚠️ Таймаут ожидания деплоя${NC}"
    return 1
}

# Функция для мониторинга логов
monitor_logs() {
    echo -e "${BLUE}📊 Мониторинг логов приложения...${NC}"
    echo -e "${YELLOW}💡 Нажмите Ctrl+C для выхода из мониторинга${NC}"
    
    # Запускаем мониторинг логов в фоне
    railway logs --deployment | while read -r line; do
        # Выделяем разные типы логов цветами
        if echo "$line" | grep -q "ERROR\|CRITICAL\|❌"; then
            echo -e "${RED}$line${NC}"
        elif echo "$line" | grep -q "WARNING\|WARN\|⚠️"; then
            echo -e "${YELLOW}$line${NC}"
        elif echo "$line" | grep -q "INFO\|✅\|🚀"; then
            echo -e "${GREEN}$line${NC}"
        elif echo "$line" | grep -q "DEBUG\|🔍"; then
            echo -e "${BLUE}$line${NC}"
        else
            echo "$line"
        fi
        
        # Проверяем на crash события
        if echo "$line" | grep -q "CRASH\|EXCEPTION\|💥"; then
            echo -e "${RED}🚨 ОБНАРУЖЕН КРАШ В ПРИЛОЖЕНИИ!${NC}"
            echo -e "${YELLOW}📱 Система crash handling должна автоматически обработать это${NC}"
        fi
    done
}

# Основной процесс деплоя
echo -e "${BLUE}📦 Запуск деплоя на Railway...${NC}"

# Выполняем деплой
if railway up --detach; then
    echo -e "${GREEN}✅ Деплой инициирован успешно${NC}"
    
    # Проверяем статус
    if check_deployment_status; then
        echo -e "${GREEN}🎉 Приложение успешно развернуто!${NC}"
        
        # Получаем URL приложения
        APP_URL=$(railway status --json | jq -r '.deployments[0].url' 2>/dev/null || echo "URL недоступен")
        if [ "$APP_URL" != "null" ] && [ "$APP_URL" != "URL недоступен" ]; then
            echo -e "${BLUE}🌐 URL приложения: ${GREEN}$APP_URL${NC}"
        fi
        
        echo -e "${BLUE}📋 Полезные команды:${NC}"
        echo -e "${YELLOW}  railway logs          ${NC}# Просмотр логов"
        echo -e "${YELLOW}  railway logs --json   ${NC}# Логи в JSON формате"
        echo -e "${YELLOW}  railway ssh           ${NC}# SSH в контейнер"
        echo -e "${YELLOW}  railway status        ${NC}# Статус сервиса"
        echo -e "${YELLOW}  railway variables     ${NC}# Переменные окружения"
        
        # Предлагаем мониторинг логов
        echo ""
        read -p "🤔 Хотите запустить мониторинг логов? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            monitor_logs
        fi
        
    else
        echo -e "${RED}❌ Деплой завершился с ошибками${NC}"
        echo -e "${YELLOW}📊 Проверьте логи: railway logs${NC}"
        exit 1
    fi
    
else
    echo -e "${RED}❌ Ошибка при инициации деплоя${NC}"
    exit 1
fi

echo -e "${GREEN}🎊 Скрипт деплоя завершен!${NC}"
