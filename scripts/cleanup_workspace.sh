#!/bin/bash

echo "🧹 Начинаем очистку workspace..."

# Создаем папку для архива (на случай если что-то нужно)
mkdir -p archive

# Функция для безопасного перемещения файлов
safe_move() {
    if [ -f "$1" ]; then
        mv "$1" archive/ 2>/dev/null
        echo "📦 Архивирован: $1"
    fi
}

# Функция для безопасного удаления файлов
safe_remove() {
    if [ -f "$1" ]; then
        rm "$1" 2>/dev/null
        echo "🗑️ Удален: $1"
    fi
}

echo ""
echo "📦 Архивируем тестовые файлы..."

# Тестовые файлы
safe_move "auth_test_results_20250727_180116.json"
safe_move "auth_test.log"
safe_move "final_auth_test_results_20250727_180632.json"
safe_move "final_auth_test.log"
safe_move "final_auth_test.py"
safe_move "simple_auth_test.py"
safe_move "test_admin.py"
safe_move "test_auth_comprehensive.py"
safe_move "test_auth.py"
safe_move "test_complete.py"
safe_move "test_integration.py"
safe_move "test_optimization.py"
safe_move "test_parser.py"
safe_move "test_webapp.py"
safe_move "test_bot_auth.py"
safe_move "test_bot_dry_run.py"
safe_move "test_bot_functionality.py"
safe_move "test_local_functionality.py"
safe_move "test_full_functionality.py"

echo ""
echo "🔬 Архивируем экспериментальные файлы..."

# Экспериментальные файлы
safe_move "demo_bot.py"
safe_move "explore_booking_process.py"
safe_move "check_webapp_urls.py"
safe_move "find_url.py"
safe_move "quick_url_test.py"
safe_move "create_log_bot.py"
safe_move "webapp_test.html"

echo ""
echo "📄 Удаляем дублирующиеся документы..."

# Дублирующиеся документы
safe_remove "README_DEPLOY.md"
safe_remove "DEPLOY.md"

echo ""
echo "📚 Перемещаем отчеты в docs/..."

# Перемещаем отчеты в docs
[ -f "TESTING_REPORT.md" ] && mv "TESTING_REPORT.md" docs/ && echo "📚 Перемещен: TESTING_REPORT.md"
[ -f "COMPLETION_REPORT.md" ] && mv "COMPLETION_REPORT.md" docs/ && echo "📚 Перемещен: COMPLETION_REPORT.md"
[ -f "INTEGRATION_COMPLETION_REPORT.md" ] && mv "INTEGRATION_COMPLETION_REPORT.md" docs/ && echo "📚 Перемещен: INTEGRATION_COMPLETION_REPORT.md"
[ -f "FINAL_TEST_REPORT.md" ] && mv "FINAL_TEST_REPORT.md" docs/ && echo "📚 Перемещен: FINAL_TEST_REPORT.md"
[ -f "WEBAPP_COMPLETION_REPORT.md" ] && mv "WEBAPP_COMPLETION_REPORT.md" docs/ && echo "📚 Перемещен: WEBAPP_COMPLETION_REPORT.md"
[ -f "WEBAPP_FINAL_FIX.md" ] && mv "WEBAPP_FINAL_FIX.md" docs/ && echo "📚 Перемещен: WEBAPP_FINAL_FIX.md"
[ -f "WEBAPP_FIX_REPORT.md" ] && mv "WEBAPP_FIX_REPORT.md" docs/ && echo "📚 Перемещен: WEBAPP_FIX_REPORT.md"
[ -f "WEBAPP_UPDATE_GUIDE.md" ] && mv "WEBAPP_UPDATE_GUIDE.md" docs/ && echo "📚 Перемещен: WEBAPP_UPDATE_GUIDE.md"

echo ""
echo "🗑️ Удаляем устаревшие файлы..."

# Устаревшие файлы в src
safe_remove "src/bot_backup.py"
safe_remove "src/requests_auth_backup.py"
safe_remove "src/clean_auth.py"
safe_remove "src/fixed_auth.py"
safe_remove "src/improved_auth.py"
safe_remove "src/improved_bot.py"

# JSON файлы сессий (кроме примеров)
safe_move "test_session.json"
safe_move "user_sessions.json"

echo ""
echo "🧹 Очистка завершена!"
echo ""
echo "📁 Итоговая структура:"
echo "├── src/"
echo "│   ├── bot.py                 # Основной бот"
echo "│   ├── parser.py              # Парсер расписаний"
echo "│   ├── requests_auth.py       # Авторизация"
echo "│   ├── bot_auth_manager.py    # Веб-авторизация"
echo "│   ├── improved_web_auth.py   # Улучшенная авторизация"
echo "│   ├── auto_booking.py        # Автобронирование"
echo "│   ├── admin_panel.py         # Админ-панель"
echo "│   ├── log_manager.py         # Логирование"
echo "│   └── ticket_formatter.py    # Форматирование"
echo "├── tests/"
echo "│   └── test_bot.py           # Основные тесты"
echo "├── docs/"
echo "│   ├── DEPLOYMENT.md         # Развертывание"
echo "│   ├── USER_GUIDE.md         # Руководство"
echo "│   ├── TESTING_GUIDE.md      # Тестирование"
echo "│   └── *.md                  # Отчеты и документация"
echo "├── scripts/"
echo "│   └── start_bot.sh          # Запуск бота"
echo "├── logs/"
echo "│   └── bot.log               # Логи"
echo "├── archive/"
echo "│   └── ...                   # Архивированные файлы"
echo "└── requirements.txt          # Зависимости"
