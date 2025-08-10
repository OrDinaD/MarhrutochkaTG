# 🚂 Railway-оптимизированная система логирования

## 📋 Обзор

Новая система логирования специально разработана для красивого отображения логов в Railway консоли. Использует JSON структурированное логирование с правильной маршрутизацией stdout/stderr для корректной цветовой индикации.

## 🎯 Основные возможности

### ✅ Автоматическое определение окружения
- **Railway**: Использует `RailwayLogger` с JSON форматированием
- **Локальная разработка**: Стандартное логирование с файлами

### 🌈 Цветовая индикация в Railway
- 🟢 **Зеленые** (stdout): INFO, WARNING, ERROR, CRITICAL
- 🔘 **Серые** (stderr): DEBUG

### 📊 JSON структура логов
```json
{
  "timestamp": "2025-08-10T14:54:40.246799+00:00",
  "level": "info",
  "message": "🤖 Пользователь подключился",
  "logger": "TestBot",
  "service": "test-service",
  "replica_id": "test-replica", 
  "region": "us-west1",
  "user_id": {"user_id": 12345, "username": "test_user"},
  "action": "bot_action"
}
```

## 🔧 Использование

### Основное логирование

```python
from src.log_manager import setup_logging

# Автоматически определяет Railway и настраивает соответствующий логгер
logger = setup_logging()

# Обычные методы
logger.info("Информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка", exc_info=True)
logger.debug("Отладочная информация")
```

### Специализированные методы логирования

```python
# В Railway окружении доступны специальные методы
if isinstance(logger, RailwayLogger):
    # Действия бота
    logger.bot_action("Пользователь подключился", {
        "user_id": 12345,
        "username": "test_user"
    })
    
    # Аутентификация
    logger.auth_action("Успешная авторизация", {
        "user_id": 12345,
        "method": "telegram"
    })
    
    # Парсинг данных
    logger.parser_action("Парсинг завершен", {
        "routes_found": 15,
        "processing_time": 2.5
    })
    
    # Действия администратора
    logger.admin_action("Пользователь заблокирован", {
        "admin_id": 99999,
        "target_user": 12345,
        "reason": "spam"
    })
```

### Измерение времени выполнения

```python
# Декоратор для функций
@logger.measure_time("database_query")
def get_user_data(user_id):
    # Код функции
    return data

# Контекстный менеджер
with logger.time_context("api_request"):
    response = api_call()
```

### Быстрые функции

```python
from src.railway_logger import log_info, log_error, bot_action

# Быстрое логирование
log_info("Система запущена")
log_error("Критическая ошибка", operation="startup")

# Специализированные действия
bot_action("Новый пользователь", {"user_id": 123})
```

## 🛠 Настройка переменных окружения

### Railway (автоматически)
```bash
RAILWAY_SERVICE_NAME=marhrutochka-bot
RAILWAY_REPLICA_ID=replica-123
RAILWAY_REPLICA_REGION=us-west1
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Локальная разработка
```bash
LOG_LEVEL=DEBUG
LOG_BOT_TOKEN=your_log_bot_token      # Опционально для Telegram логов
LOG_CHAT_ID=your_admin_chat_id        # Опционально для Telegram логов
```

## 📁 Структура файлов

```
src/
├── railway_logger.py      # Основная система Railway логирования
├── log_manager.py         # Менеджер логирования с автоопределением
└── bot.py                 # Интегрированное логирование в боте

test_railway_logging.py    # Демонстрация и тестирование
```

## 🎮 Демонстрация

Запустите тест системы:

```bash
python3 test_railway_logging.py
```

Вывод покажет все типы логов в Railway-совместимом JSON формате.

## ⚡ Производительность

- **JSON сериализация**: Быстрая с `ensure_ascii=False`
- **Буферизация**: Автоматическая для stdout/stderr
- **Метаданные**: Кешируются при инициализации
- **Асинхронность**: Не блокирует основной поток

## 🔍 Отладка

### Проверка типа логгера
```python
from src.railway_logger import RailwayLogger

logger = setup_logging()
is_railway = isinstance(logger, RailwayLogger)
print(f"Используется Railway логгер: {is_railway}")
```

### Проверка переменных окружения
```python
import os
railway_vars = {
    'SERVICE_NAME': os.getenv('RAILWAY_SERVICE_NAME'),
    'REPLICA_ID': os.getenv('RAILWAY_REPLICA_ID'),
    'REGION': os.getenv('RAILWAY_REPLICA_REGION'),
    'LOG_LEVEL': os.getenv('LOG_LEVEL')
}
print(railway_vars)
```

## 📚 API Reference

### RailwayLogger методы

| Метод | Описание | Параметры |
|-------|----------|-----------|
| `info(msg, **kwargs)` | Информационное сообщение | message, extra fields |
| `warning(msg, **kwargs)` | Предупреждение | message, extra fields |
| `error(msg, exc_info=None, **kwargs)` | Ошибка | message, exception info, extra |
| `debug(msg, **kwargs)` | Отладка | message, extra fields |
| `success(msg, **kwargs)` | Успешная операция | message, extra fields |
| `bot_action(msg, data, level)` | Действие бота | message, user data, log level |
| `auth_action(msg, data, level)` | Аутентификация | message, auth data, log level |
| `parser_action(msg, data, level)` | Парсинг | message, parsing data, log level |
| `admin_action(msg, data, level)` | Админ действие | message, admin data, log level |
| `measure_time(operation)` | Декоратор времени | operation name |
| `time_context(operation)` | Контекст времени | operation name |

## 🔄 Обратная совместимость

Все существующие вызовы `logger.info()`, `logger.error()` и т.д. продолжают работать без изменений. Новые методы доступны только в Railway окружении.

## 🛡 Безопасность

- Автоматическая фильтрация чувствительных данных
- Контроль размера логов (JSON сериализация)
- Защита от циклических ссылок в объектах
- Безопасное форматирование исключений
