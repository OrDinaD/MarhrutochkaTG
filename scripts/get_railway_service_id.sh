#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Получение Railway Service ID${NC}"
echo "=================================="
echo ""

# Проверяем Railway CLI
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ Railway CLI не установлен!${NC}"
    echo -e "${YELLOW}💡 Установите: npm install -g @railway/cli${NC}"
    echo "   или: curl -fsSL https://railway.app/install.sh | sh"
    exit 1
fi

# Проверяем авторизацию
if ! railway whoami &> /dev/null; then
    echo -e "${RED}❌ Не авторизованы в Railway!${NC}"
    echo -e "${YELLOW}💡 Выполните: railway login${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Railway CLI авторизован${NC}"
echo ""

# Проверяем что мы в проекте Railway
if ! railway status &> /dev/null; then
    echo -e "${RED}❌ Текущая директория не связана с Railway проектом!${NC}"
    echo -e "${YELLOW}💡 Выполните: railway link${NC}"
    exit 1
fi

# Получаем информацию о проекте
echo -e "${BLUE}📋 Информация о проекте:${NC}"
railway status

echo ""
echo -e "${BLUE}🔑 Получение Service ID...${NC}"

# Получаем список сервисов
SERVICES_JSON=$(railway service list --json 2>/dev/null)

if [ -z "$SERVICES_JSON" ]; then
    echo -e "${YELLOW}⚠️  Не удалось получить список сервисов${NC}"
    echo ""
    echo -e "${BLUE}💡 Способы получить Service ID:${NC}"
    echo ""
    echo "1. Через Railway Dashboard:"
    echo "   Откройте ваш проект в браузере"
    echo "   URL будет выглядеть так:"
    echo "   https://railway.app/project/[PROJECT_ID]/service/[SERVICE_ID]"
    echo "                                                        ^^^^^^^^^^^"
    echo ""
    echo "2. Service ID автоматически доступен в переменной RAILWAY_SERVICE_ID"
    echo "   при деплое на Railway (внутри контейнера)"
else
    # Парсим JSON если есть jq
    if command -v jq &> /dev/null; then
        SERVICE_ID=$(echo "$SERVICES_JSON" | jq -r '.[0].id' 2>/dev/null)
        SERVICE_NAME=$(echo "$SERVICES_JSON" | jq -r '.[0].name' 2>/dev/null)
        
        if [ -n "$SERVICE_ID" ] && [ "$SERVICE_ID" != "null" ]; then
            echo -e "${GREEN}✅ Service ID найден!${NC}"
            echo ""
            echo -e "${BLUE}Service Name:${NC} $SERVICE_NAME"
            echo -e "${BLUE}Service ID:${NC} $SERVICE_ID"
            echo ""
            echo -e "${YELLOW}💡 Добавьте эту переменную в Railway Dashboard:${NC}"
            echo "   RAILWAY_SERVICE_ID=$SERVICE_ID"
        else
            echo -e "${YELLOW}⚠️  Service ID не найден в ответе${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  jq не установлен, не могу распарсить JSON${NC}"
        echo ""
        echo "Установите jq: brew install jq (macOS) или apt install jq (Linux)"
        echo ""
        echo "Или получите Service ID вручную из Railway Dashboard"
    fi
fi

echo ""
echo -e "${BLUE}📊 Проверка текущих переменных:${NC}"
railway variables 2>/dev/null | grep -E "(RAILWAY_SERVICE_ID|ADMIN_TELEGRAM_ID|RAILWAY_TOKEN)" || echo "Переменные не найдены или недоступны"

echo ""
echo -e "${BLUE}💡 Для команды /reload в боте нужны:${NC}"
echo "  1. RAILWAY_TOKEN - Railway API токен"
echo "  2. RAILWAY_SERVICE_ID - ID этого сервиса"
echo "  3. ADMIN_TELEGRAM_ID - ID администратора бота"
