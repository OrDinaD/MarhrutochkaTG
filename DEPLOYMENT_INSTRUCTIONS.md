# 🚀 Инструкции по развертыванию MarhrutochkaTG

## ✅ Предварительные требования

- Python 3.8+
- Git
- Telegram Bot Token (получить у @BotFather)
- Аккаунт на сайте билет.маршруточка.бел

## 📦 Установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/OrDinaD/MarhrutochkaTG.git
cd MarhrutochkaTG
```

### 2. Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# или для Windows: venv\Scripts\activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Установка браузера Playwright
```bash
playwright install chromium
```

## 🔧 Конфигурация

### 1. Создание .env файла
```bash
cp .env.example .env
```

### 2. Настройка переменных окружения
Отредактируйте файл `.env`:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather

# Monitoring Configuration
MONITORING_ENABLED=true
MONITORING_INTERVAL_MINUTES=5
ALERT_THRESHOLD_SEATS=5

# Настройки авторизации
DEFAULT_PHONE=+375299605390
DEFAULT_PASSWORD=Zxcvbnm,1

# Настройки Playwright
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT=30000
```

### 3. Получение токена бота
1. Откройте Telegram и найдите @BotFather
2. Отправьте `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте токен в файл `.env`

## 🧪 Тестирование

### 1. Запуск демонстрационного скрипта
```bash
python scripts/demo_updated.py
```

Этот скрипт проверит:
- Авторизацию на сайте
- Форматирование билетов и профиля (демо-данные)
- Поиск маршрутов (демо-данные)
- Проверку статуса бронирования

⚠️ **Важно**: В текущей версии AuthManager есть проблемы с сохранением сессий между переходами страниц. Профиль и бронирования пока извлекаются как демо-данные. Для работы с реальными данными используйте браузерную автоматизацию через Playwright MCP.

### 2. Реальная работа с сайтом
Для работы с реальными данными профиля и бронирований используйте:
```bash
# Через Playwright MCP (рекомендуется для разработки)
python -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        # Здесь можно делать реальные тесты
        await browser.close()

asyncio.run(test())
"
```

### 2. Проверка зависимостей
```bash
python -c "import playwright; print('Playwright установлен')"
python -c "import telegram; print('python-telegram-bot установлен')"
```

## 🚀 Запуск

### 1. Запуск бота
```bash
python main.py
```

### 2. Проверка работы бота
1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Протестируйте основные команды

## 📱 Доступные команды

### Основные команды:
- `/start` - главное меню
- `/help` - справка

### Авторизация и профиль:
- `/login` - вход в аккаунт
- `/profile` - просмотр профиля
- `/bookings` - список бронирований
- `/check_booking` - проверка статуса бронирования
- `/logout` - выход из аккаунта

### Поиск и мониторинг:
- `/search` - поиск маршрутов
- `/monitoring` - настройка мониторинга

## 🔍 Диагностика проблем

### Общие проблемы:

#### 1. "Токен не работает"
- Проверьте, что токен скопирован правильно
- Убедитесь, что в `.env` файле нет лишних пробелов
- Проверьте, что бот не заблокирован

#### 2. "Playwright не работает"
```bash
# Переустановите браузер
playwright install chromium --force
```

#### 3. "Авторизация не работает"
- Проверьте учетные данные в `.env`
- Убедитесь, что аккаунт существует на сайте
- Проверьте, что сайт доступен

#### 4. "Модуль не найден"
```bash
# Переустановите зависимости
pip install -r requirements.txt --force-reinstall
```

### Логи и отладка:
```bash
# Запуск с подробными логами
python main.py --log-level DEBUG

# Проверка логов
tail -f logs/bot.log  # если логи записываются в файл
```

## 🖥️ Развертывание на сервере

### 1. Systemd (Linux)
Создайте файл `/etc/systemd/system/marhrutochka-bot.service`:

```ini
[Unit]
Description=MarhrutochkaTG Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/MarhrutochkaTG
Environment=PATH=/path/to/MarhrutochkaTG/venv/bin
ExecStart=/path/to/MarhrutochkaTG/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl daemon-reload
sudo systemctl enable marhrutochka-bot
sudo systemctl start marhrutochka-bot
```

### 2. Docker
Создайте `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium

COPY . .

CMD ["python", "main.py"]
```

Сборка и запуск:
```bash
docker build -t marhrutochka-bot .
docker run -d --name marhrutochka-bot --env-file .env marhrutochka-bot
```

## 🔄 Обновление

### 1. Получение обновлений
```bash
git pull origin main
pip install -r requirements.txt
```

### 2. Перезапуск бота
```bash
# Если запущен вручную
# Остановите бот (Ctrl+C) и запустите снова
python main.py

# Если используется systemd
sudo systemctl restart marhrutochka-bot

# Если используется Docker
docker restart marhrutochka-bot
```

## 🛡️ Безопасность

### Рекомендации:
1. **Не публикуйте .env файл** - добавьте его в `.gitignore`
2. **Используйте отдельные учетные данные** для бота
3. **Регулярно обновляйте зависимости**
4. **Мониторьте логи** на предмет ошибок

### Создание резервной копии:
```bash
# Создание архива
tar -czf marhrutochka-backup-$(date +%Y%m%d).tar.gz \
  --exclude='venv' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  .
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи приложения
2. Убедитесь, что все зависимости установлены
3. Проверьте настройки в `.env`
4. Изучите файл `IMPLEMENTATION_REPORT.md`

## 🎉 Готово!

Ваш бот MarhrutochkaTG готов к использованию! 

Основные возможности:
- ✅ Авторизация на сайте
- ✅ Просмотр профиля
- ✅ Поиск маршрутов
- ✅ Мониторинг рейсов
- ✅ Проверка бронирований
- ✅ Красивое форматирование

Наслаждайтесь использованием! 🚌
