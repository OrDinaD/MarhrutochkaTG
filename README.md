# 🚌 MarhrutochkaTG Bot

> **Продвинутый Telegram-бот** для автоматического мониторинга и поиска билетов на маршрутки **Минск ↔ Островец** с интеллектуальной системой уведомлений и crash-recovery архитектурой.

<div align="center">

![Интерфейс бота](assets/interface.jpg)

[![Railway Deploy](https://img.shields.io/badge/Deploy-Railway-blueviolet)](https://railway.app/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg)](https://core.telegram.org/bots/api)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ✨ Ключевые особенности

### 🎯 **Умный мониторинг**
- ⚡ **Async парсинг** с `aiohttp` для высокой производительности  
- 🕒 **Адаптивные интервалы** - быстрее в часы пик, реже ночью
- 🔄 **Auto-recovery система** - самовосстановление после сбоев
- 📊 **Real-time уведомления** при появлении свободных мест

### 🛡️ **Production-ready архитектура**
- 🔐 **Безопасный callback routing** с таймаутами и защитой от зависаний
- 📝 **Railway Enhanced Logger** с JSON структурированными логами  
- 🚨 **Crash Handler** с автоматическими отчетами и диагностикой
- ⚙️ **Memory-only architecture** - никаких БД, только in-memory state

### 🎨 **Продвинутый UX**
- 📱 **Responsive inline клавиатуры** с динамическим обновлением
- 🔍 **Smart поиск** с фильтрами по времени и дате
- 👤 **Персональные профили** с сохранением предпочтений
- 🎛️ **Админ-панель** с мониторингом системы в реальном времени

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

- **Memory footprint**: ~15-20MB в рабочем состоянии
- **Response time**: <200ms для большинства операций  
- **Concurrent users**: До 100+ одновременных пользователей
- **Monitoring interval**: 30 сек в часы пик, 5 мин в ночное время
- **Auto-recovery**: <10 сек восстановление после сбоев

</details>

---

## 🚀 Быстрый старт

### 🐳 Railway (Recommended)

```bash
# 1. Fork этот репозиторий
# 2. Подключите к Railway
# 3. Добавьте environment variables:
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_TELEGRAM_ID=your_telegram_id
```

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

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
| `LOG_LEVEL` | ❌ | Уровень логирования | `INFO` / `DEBUG` / `ERROR` |
| `DEVELOPMENT_MODE` | ❌ | Режим разработки | `true` / `false` |
| `MONITORING_INTERVAL` | ❌ | Интервал мониторинга (сек) | `30` |
| `MAX_CONCURRENT_MONITORS` | ❌ | Макс. одновременных мониторов | `50` |

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

## 🎯 Команды и функции

### 🤖 Пользовательские команды
- `/start` - **Главное меню** с приветствием и навигацией
- `/search` - **Поиск рейсов** с интерактивными фильтрами  
- `/monitor` - **Создать мониторинг** с настройкой уведомлений
- `/profile` - **Личный кабинет** с историей и настройками
- `/help` - **Справочная система** с подробными инструкциями

### 👨‍💻 Админ-команды  
- `/admin` - **Панель администратора** с системным мониторингом
- `/stats` - **Статистика** пользователей и производительности
- `/logs` - **Просмотр логов** в реальном времени
- `/recovery` - **Ручной запуск** системы восстановления

---

## 🔬 Технические детали

### 📊 **Monitoring Stack**
```python
# Real-time системный мониторинг
├── RailwayLoggerEnhanced     # Structured JSON logging
├── CrashHandler              # Exception capture & analysis  
├── AutoRecoverySystem        # Self-healing mechanisms
├── DiagnosticSystem          # Health checks & alerts
└── CallbackTracker           # UI state management
```

### 🌐 **Parser Architecture**  
```python
# Async web scraping pipeline
class FinalMarshrutochkaParser:
    ├── aiohttp.ClientSession    # Async HTTP client
    ├── BeautifulSoup4          # HTML parsing 
    ├── Smart caching           # Response optimization
    └── Error resilience        # Retry mechanisms
```

### 🛡️ **Security Features**
- **Input validation** всех пользовательских данных
- **Rate limiting** для предотвращения спама
- **Callback query protection** от race conditions  
- **Safe API wrappers** с automatic retry logic
- **Memory leak prevention** с automatic cleanup

---

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# Тесты с покрытием
pytest --cov=src --cov-report=html

# Интеграционные тесты
pytest tests/test_bot.py -v

# Performance тесты  
pytest tests/test_monitoring.py::test_performance -s
```

**Test Coverage**: 85%+ основного функционала

---

## 📈 Мониторинг и метрики

### 🔍 **Railway Logs**
```json
{
  "timestamp": "2024-12-12T12:32:50.123Z",
  "level": "INFO", 
  "component": "bot",
  "action": "user_search",
  "user_id": 123456789,
  "data": {
    "search_params": {"from": "Минск", "to": "Островец"},
    "execution_time": "1.23s",
    "results_found": 5
  }
}
```

### 📊 **Системные метрики**
- 🔄 **Uptime tracking** с автоматическими health checks
- 📱 **User activity** с детализацией по функциям  
- ⚡ **Performance profiling** всех критических операций
- 🚨 **Error rate monitoring** с алертами

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
- **Python**: PEP 8 + Black formatting  
- **Docstrings**: Google style
- **Type hints**: обязательны для public методов
- **Async/await**: предпочтительно для I/O операций

---

## 📞 Поддержка

### 🔧 **Troubleshooting**
1. Проверьте [logs](data/logs/) на наличие ошибок
2. Убедитесь в корректности [environment variables](#-environment-variables)
3. Проверьте [Railway status](https://status.railway.app/) при деплое  
4. Посмотрите [открытые issues](../../issues) для известных проблем

### 📚 **Документация**
- [Deployment Guide](RAILWAY_SETUP.md) - детальный гайд по деплою
- [API Reference](docs/) - техническая документация
- [Testing Guide](tests/TEST_REPORT.md) - руководство по тестированию

### 💬 **Связь**
- **Issues**: [GitHub Issues](../../issues) для багов и feature requests
- **Discussions**: [GitHub Discussions](../../discussions) для вопросов
- **Email**: создайте issue для контакта с разработчиком

---

<div align="center">

**Made with ❤️ for Belarus 🇧🇾**

*Этот проект создан для упрощения поездок между Минском и Островцом*

[⭐ Star this repo](../../stargazers) | [🍴 Fork](../../fork) | [📝 Issues](../../issues) | [💬 Discussions](../../discussions)

</div>
