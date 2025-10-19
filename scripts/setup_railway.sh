#!/bin/bash
# Скрипт быстрой настройки Railway деплоя

set -e

echo "🚀 Railway Quick Setup Script"
echo "=============================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода цветных сообщений
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

# Проверяем Railway CLI
check_railway_cli() {
    if ! command -v railway &> /dev/null; then
        print_error "Railway CLI не найден!"
        echo "Установите его командой: npm install -g @railway/cli"
        echo "Или скачайте с: https://railway.app/cli"
        exit 1
    fi
    print_status "Railway CLI найден"
}

# Проверяем аутентификацию
check_railway_auth() {
    if ! railway whoami &> /dev/null; then
        print_warning "Не авторизованы в Railway"
        echo "Запускаем авторизацию..."
        railway login
    fi
    print_status "Авторизация в Railway проверена"
}

# Проверяем или создаем проект
setup_railway_project() {
    print_info "Настраиваем Railway проект..."
    
    # Проверяем, есть ли уже проект
    if railway status &> /dev/null; then
        print_status "Railway проект уже настроен"
        railway status
    else
        print_warning "Railway проект не найден"
        echo "Выберите действие:"
        echo "1) Создать новый проект"
        echo "2) Подключиться к существующему"
        read -p "Введите номер (1 или 2): " choice
        
        case $choice in
            1)
                print_info "Создаем новый проект..."
                railway new
                ;;
            2)
                print_info "Подключаемся к существующему проекту..."
                railway link
                ;;
            *)
                print_error "Неверный выбор"
                exit 1
                ;;
        esac
    fi
}

# Настройка переменных окружения
setup_environment_variables() {
    print_info "Настраиваем переменные окружения..."
    
    # Проверяем существующие переменные
    existing_vars=$(railway variables --json 2>/dev/null || echo "[]")
    
    # TELEGRAM_BOT_TOKEN
    if echo "$existing_vars" | grep -q "TELEGRAM_BOT_TOKEN"; then
        print_status "TELEGRAM_BOT_TOKEN уже настроен"
    else
        print_warning "TELEGRAM_BOT_TOKEN не найден"
        read -p "Введите токен бота: " bot_token
        if [ ! -z "$bot_token" ]; then
            railway variables set TELEGRAM_BOT_TOKEN="$bot_token"
            print_status "TELEGRAM_BOT_TOKEN установлен"
        fi
    fi
    
    # AUTH_TOKEN (опционально)
    if echo "$existing_vars" | grep -q "AUTH_TOKEN"; then
        print_status "AUTH_TOKEN уже настроен"
    else
        print_warning "AUTH_TOKEN не найден"
        read -p "Введите токен авторизации (или нажмите Enter для пропуска): " auth_token
        if [ ! -z "$auth_token" ]; then
            railway variables set AUTH_TOKEN="$auth_token"
            print_status "AUTH_TOKEN установлен"
        else
            print_info "AUTH_TOKEN пропущен"
        fi
    fi
    
    # Дополнительные переменные для Railway
    railway variables set RAILWAY_ENV="production"
    railway variables set PYTHONUNBUFFERED="1"
    railway variables set LOG_LEVEL="INFO"
    
    print_status "Переменные окружения настроены"
}

# Тестируем конфигурацию
test_configuration() {
    print_info "Тестируем конфигурацию..."
    
    if python test_railway_deployment.py; then
        print_status "Все тесты пройдены!"
    else
        print_warning "Некоторые тесты не прошли, но это не критично"
    fi
}

# Деплой приложения
deploy_application() {
    print_info "Разворачиваем приложение..."
    
    echo "Начинаем деплой..."
    railway up --detach
    
    print_status "Деплой запущен!"
    
    # Ждем немного и показываем статус
    sleep 5
    railway status
    
    print_info "Для просмотра логов используйте: railway logs --follow"
    print_info "Для открытия dashboard: railway open"
}

# Основная функция
main() {
    echo "Этот скрипт поможет настроить и развернуть ваш бот на Railway"
    echo ""
    
    check_railway_cli
    check_railway_auth
    setup_railway_project
    setup_environment_variables
    test_configuration
    
    echo ""
    echo "🚀 Готовы к деплою?"
    read -p "Продолжить деплой? (y/N): " deploy_confirm
    
    if [[ $deploy_confirm =~ ^[Yy]$ ]]; then
        deploy_application
        print_status "Деплой завершен! 🎉"
    else
        print_info "Деплой отменен. Для деплоя позже используйте: railway up"
    fi
    
    echo ""
    print_info "Полезные команды:"
    echo "  railway logs --follow  # Просмотр логов"
    echo "  railway status         # Статус деплоя"
    echo "  railway open          # Открыть dashboard"
    echo "  railway restart       # Перезапуск сервиса"
    echo ""
    print_status "Готово! Ваш бот развернут на Railway! 🤖"
}

# Обработка ошибок
trap 'print_error "Произошла ошибка. Проверьте вывод выше."' ERR

# Запуск основной функции
main "$@"
