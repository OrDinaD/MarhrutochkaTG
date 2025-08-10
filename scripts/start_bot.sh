#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚌 Скрипт запуска Telegram-бота мониторинга маршруточки v2.0${NC}"
echo -e "${BLUE}===========================================${NC}"

# Получаем директорию проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo -e "${YELLOW}📁 Рабочая директория: ${PROJECT_DIR}${NC}"

# Функция для проверки существования файла
check_file() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}❌ Файл не найден: $1${NC}"
        return 1
    fi
    return 0
}

# Проверка основных файлов
echo -e "
${BLUE}� Проверка файлов...${NC}"

required_files=(
    "main.py"
    "src/bot.py"
    "src/parser.py"
    "requirements.txt"
)

for file in "${required_files[@]}"; do
    if check_file "$file"; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ Критический файл отсутствует: $file${NC}"
        exit 1
    fi
done

# Проверка .env файла
echo -e "
${BLUE}⚙️ Проверка конфигурации...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ Файл .env не найден${NC}"
    if [ -f ".env.example" ]; then
        echo -e "${CYAN}� Найден .env.example, создаю .env...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}📝 Отредактируйте .env и укажите ваш TELEGRAM_BOT_TOKEN${NC}"
        exit 1
    else
        echo -e "${RED}❌ Необходимо создать .env файл с токеном бота${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env файл найден${NC}"
fi

# Проверка токена
if grep -q "your_bot_token_here" .env; then
    echo -e "${YELLOW}⚠️ Необходимо указать реальный токен в .env файле${NC}"
    exit 1
fi

# Проверка Python зависимостей
echo -e "
${BLUE}📦 Проверка зависимостей...${NC}"
if ! python -c "import telegram; import aiohttp; import asyncio; print('✅ Основные зависимости установлены')" 2>/dev/null; then
    echo -e "${YELLOW}⚠️ Устанавливаю зависимости...${NC}"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Ошибка установки зависимостей${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Зависимости установлены${NC}"
fi

# Быстрый тест бота
echo -e "
${BLUE}🧪 Быстрый тест бота...${NC}"
if python -c "from src.bot import get_main_menu_keyboard; print('✅ Бот готов к работе')" 2>/dev/null; then
    echo -e "${GREEN}✅ Бот прошел быструю проверку${NC}"
else
    echo -e "${YELLOW}⚠️ Есть проблемы с ботом, но попробуем запустить...${NC}"
fi

# Создание директорий
echo -e "
${BLUE}� Создание рабочих директорий...${NC}"
mkdir -p logs user_sessions
echo -e "${GREEN}✅ Директории созданы${NC}"

# Показ полезной информации
echo -e "
${PURPLE}💡 Полезные команды:${NC}"
echo -e "${CYAN}   • Ctrl+C - остановка бота${NC}"
echo -e "${CYAN}   • python tests/test_all.py - полное тестирование${NC}"
echo -e "${CYAN}   • tail -f logs/bot.log - просмотр логов${NC}"

# Функция graceful shutdown
cleanup() {
    echo -e "
${YELLOW}⚠️ Получен сигнал остановки...${NC}"
    echo -e "${BLUE}🛑 Завершение работы бота...${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Запуск бота
echo -e "
${GREEN}🚀 Запуск бота...${NC}"
echo -e "${BLUE}===========================================${NC}
"

# Определяем способ запуска
if [ -f "main.py" ]; then
    echo -e "${CYAN}� Запуск через main.py...${NC}"
    python main.py
else
    echo -e "${CYAN}� Прямой запуск src/bot.py...${NC}"
    python src/bot.py
fi

# Обработка завершения
exit_code=$?
echo -e "
${BLUE}===========================================${NC}"
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ Бот завершил работу корректно${NC}"
else
    echo -e "${RED}❌ Бот завершился с ошибкой (код: $exit_code)${NC}"
    echo -e "${CYAN}💡 Проверьте логи: tail logs/bot.log${NC}"
fi

echo -e "${CYAN}👋 До свидания!${NC}"
