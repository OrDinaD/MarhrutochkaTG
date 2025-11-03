# 🚌 MarhrutochkaTG Bot

<img src="assets/interface.jpg" alt="Интерфейс бота" width="300" align="left" style="margin-right: 20px; margin-bottom: 20px;">

**Telegram-бот** для мониторинга и поиска рейсов маршруток **Минск ↔ Островец**. Автоматически проверяет наличие свободных мест и отправляет уведомления, когда они появляются.

**Основные возможности:**
- 🔔 Автоматический мониторинг рейсов каждые 5 минут
- 📅 Поиск по дате и времени отправления/прибытия
- 🚀 Мгновенные уведомления о свободных местах
- 🛡️ Стабильная работа с системой восстановления после сбоев
- 📊 Админ-панель для управления и статистики

[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-238%20passed-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-36%25-yellow)](tests/)

<br clear="left"/>

---

## ✨ Возможности

### 🎯 Мониторинг рейсов
- � Автоматическая проверка наличия мест каждые 5 минут
- � Уведомления в Telegram при появлении свободных мест
- � Настройка времени отправления/прибытия
- � Выбор даты поездки

### 🔍 Поиск маршрутов
- Просмотр доступных рейсов на конкретную дату
- Фильтрация по времени отправления или прибытия
- Информация о количестве свободных мест
- Прямая ссылка на сайт бронирования

### ⚙️ Технические особенности
- Асинхронный парсинг сайта маршруточка.бел
- Система восстановления после сбоев
- In-memory хранение данных (без БД)
- Защита от зависаний callback handlers
- Логирование для Railway

---

## 🔧 Техническая архитектура

<details>
<summary><b>📁 Структура проекта</b></summary>

```tree
├── main.py                    # 🚀 Точка входа с environment validation
├── src/
│   ├── bot.py                 # 🤖 Core bot logic + callback tracking
│   ├── callback_router.py     # 🎯 Centralized callback distribution  
│   ├── security.py            # 🔒 Input validation & rate limiting
│   ├── admin_panel.py         # 👨‍💻 Real-time admin dashboard
│   ├── managers/
│   │   └── user_manager.py    # 👤 In-memory user state management
│   ├── monitoring/            # 📊 Production monitoring stack
│   │   ├── railway_logger_enhanced.py   # Railway JSON logging
│   │   ├── auto_recovery.py             # Self-healing system
│   │   ├── crash_handler.py             # Crash detection & reporting  
│   │   └── diagnostic_system.py         # Health checks & metrics
│   └── utils/
│       ├── parser.py          # 🌐 Async site scraper (aiohttp + BeautifulSoup)
│       ├── telegram_safe.py   # 🛡️ Telegram API safety wrappers
│       ├── keyboards.py       # ⌨️ Dynamic keyboard factory
│       └── route_analyzer.py  # 🧮 Schedule analysis algorithms
├── tests/                     # 🧪 Comprehensive test suite
└── scripts/                   # 🔧 Deployment & maintenance tools
```

</details>

<details>
<summary><b>⚡ Производительность</b></summary>

- **Memory footprint**: ~20-30MB в рабочем состоянии
- **Response time**: обычно < 2 секунды для большинства операций  
- **Monitoring interval**: проверка каждые 5 минут
- **Auto-recovery**: автоматическое восстановление при сбоях



---

## 🚀 Быстрый старт

### 🐳 Деплой на Railway

```bash
# 1. Fork этот репозиторий
# 2. Создайте новый проект в Railway
# 3. Подключите GitHub репозиторий
# 4. Добавьте Redis:
#    Railway Dashboard → New → Database → Add Redis
# 5. Добавьте переменные окружения:
TELEGRAM_BOT_TOKEN=ваш_токен_бота
ADMIN_TELEGRAM_ID=ваш_telegram_id
MONITORING_STORAGE=redis
```

⚠️ **Важно:** Без Redis мониторинги будут теряться при каждом деплое!  
📖 Подробнее: [docs/REDIS_SETUP.md](docs/REDIS_SETUP.md)

Railway автоматически задеплоит бота после коммита.

### 💻 Локальная разработка

```bash
# Клонирование и настройка
git clone https://github.com/OrDinaD/MarhrutochkaTG.git
cd MarhrutochkaTG

# Виртуальное окружение
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Установка зависимостей
pip install -r requirements.txt

# Для запуска тестов и утилит разработчика
pip install -r requirements.dev.txt

# Настройка окружения
cp .env.example .env
# Отредактируйте .env с вашими токенами

# Запуск
python main.py
```

---

## ⚙️ Конфигурация

<details>
<summary><b>🔐 Environment Variables</b></summary>

| Переменная | Обязательно | Описание | Пример |
|-----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Токен Telegram бота | `1234567890:ABCDEF...` |
| `ADMIN_TELEGRAM_ID` | ✅ | ID администратора | `123456789` |
| `MONITORING_STORAGE` | ⚠️ Railway | Тип хранилища (`redis` или `file`) | `redis` |
| `REDIS_URL` | ⚠️ Railway | URL Redis (автоматически от Railway) | `redis://...` |
| `LOG_LEVEL` | ❌ | Уровень логирования | `INFO` / `DEBUG` / `ERROR` |
| `MONITORING_INTERVAL` | ❌ | Интервал мониторинга (сек) | `30` |

**⚠️ Для Railway обязательно:**
- Добавьте Redis сервис в Railway dashboard
- Установите `MONITORING_STORAGE=redis`
- Иначе мониторинги будут теряться при каждом деплое!

</details>

<details>
<summary><b>🎛️ Расширенные настройки</b></summary>

```python
# src/bot.py - основные параметры
CALLBACK_TIMEOUT_SECONDS = 45      # Таймаут callback queries  
MAX_MONITORS_PER_USER = 3          # Лимит мониторов на пользователя
MONITORING_WORK_HOURS = (6, 23)    # Рабочие часы мониторинга
AUTO_RECOVERY_ATTEMPTS = 3         # Попытки авто-восстановления
CRASH_REPORT_ENABLED = True        # Включить crash reports
```

</details>

---

## 🎯 Использование

### 🤖 Команды бота
- `/start` - Главное меню и начало работы
- Кнопка **"🔔 Настроить мониторинг"** - настройка автоматической проверки рейсов
- Кнопка **"🔍 Поиск рейсов"** - разовый поиск доступных мест
- Кнопка **"📊 Мои мониторинги"** - просмотр и управление активными мониторингами

### 👨‍💻 Для администратора  
- Кнопка **"⚙️ Админ-панель"** - статистика пользователей и мониторингов
- Просмотр системных логов
- Управление мониторингами всех пользователей

---

## 🔬 Технические детали

### 📊 Мониторинг и логирование
- **Railway Logger** - структурированное логирование для Railway
- **Crash Handler** - автоматические отчеты об ошибках
- **Auto Recovery** - система самовосстановления
- **Callback Tracker** - отслеживание состояний UI

### 🌐 Парсинг данных
- **aiohttp** - асинхронные HTTP запросы
- **BeautifulSoup4** - парсинг HTML
- Кэширование ответов для оптимизации
- Retry механизмы при ошибках

### 🛡️ Безопасность
- Валидация всех пользовательских данных
- Защита callback handlers от зависаний
- Безопасные обертки для Telegram API
- Автоматическая очистка памяти

---

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# Тесты с покрытием
pytest --cov=src --cov-report=html

# Конкретные тесты
pytest tests/test_bot_callbacks.py -v
```

**Статистика тестов**: 238 тестов, покрытие 36%

---

## 📈 Мониторинг

### 🔍 Логи Railway
Бот пишет структурированные JSON логи для Railway с информацией о:
- Действиях пользователей
- Ошибках и исключениях
- Времени выполнения операций
- Результатах парсинга

### 📊 Метрики
- Отслеживание активных мониторингов
- Статистика по пользователям
- Логирование ошибок
- Health checks системы

---

## 🤝 Contributing

Мы приветствуем вклад в развитие проекта! 

### 🛠️ **Development Workflow**
1. **Fork** репозиторий
2. **Create branch**: `git checkout -b feature/amazing-feature`  
3. **Make changes** с соблюдением code style
4. **Add tests** для новой функциональности
5. **Run tests**: `pytest`
6. **Commit**: `git commit -m "feat: add amazing feature"`
7. **Push**: `git push origin feature/amazing-feature`
8. **Create Pull Request**

### 📝 **Code Style**
- **Python**: PEP 8
- **Docstrings**: где необходимо
- **Async/await**: для I/O операций

---

## 📞 Поддержка

### 🔧 Troubleshooting
1. Проверьте логи в Railway dashboard
2. Убедитесь что переменные окружения установлены правильно
3. Проверьте [открытые issues](../../issues) для известных проблем

###  Связь
- **Issues**: [GitHub Issues](../../issues) для багов и предложений
- **Discussions**: [GitHub Discussions](../../discussions) для вопросов

---

<div align="center">

**Made with ❤️ for Belarus 🇧🇾**

*Этот проект создан для упрощения поездок между Минском и Островцом*

[⭐ Star this repo](../../stargazers) | [🍴 Fork](../../fork) | [📝 Issues](../../issues) | [💬 Discussions](../../discussions)

</div>
