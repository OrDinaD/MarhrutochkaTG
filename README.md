# 🚌 MarhrutochkaTG - Telegram Bot для мониторинга маршруток

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-Latest-blue)](https://core.telegram.org/bots/api)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Telegram-бот для автоматического мониторинга рейсов между Минском и Островцом** на сайте [билет.маршруточка.бел](https://билет.маршруточка.бел)

## 🎯 Основные возможности

- 🔍 **Поиск рейсов** - быстрый поиск доступных рейсов по дате
- 🔔 **Автоматический мониторинг** - проверка каждые 5 минут
- ⏰ **Гибкие настройки** - выбор времени отправления/прибытия
- 📱 **Уведомления** - мгновенные уведомления при появлении мест
- 🎨 **Современный интерфейс** - инлайн-кнопки и user-friendly UX

## 🚀 Быстрый старт

### 1. Установка

```bash
git clone https://github.com/OrDinaD/MarhrutochkaTG.git
cd MarhrutochkaTG
```

### 2. Настройка окружения

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или для Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Конфигурация

Скопируйте `.env.example` в `.env` и укажите токен вашего бота:

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
```

**Как получить токен:**
1. Напишите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен в `.env`

### 4. Запуск

**Быстрый запуск:**
```bash
chmod +x scripts/start_bot.sh
./scripts/start_bot.sh
```

**Или вручную:**
```bash
source venv/bin/activate
python main.py
```

## 📖 Использование

### Команды бота:
- `/start` - главное меню
- `/monitoring` - управление мониторингом
- `/help` - справка

### Быстрый поиск:
Отправьте дату в формате `YYYY-MM-DD` (например: `2025-07-15`) для поиска рейсов.

### Настройка мониторинга:
1. **📅 Дата** - выберите дату поездки
2. **🛣️ Направление** - Минск→Островец, Островец→Минск, или оба
3. **⏰ Тип времени** - отправление, прибытие, или любое
4. **🕐 Диапазон времени** - утром, днём, вечером, или пользовательский
5. **✅ Подтверждение** - запуск мониторинга

Бот будет проверять рейсы каждые 5 минут и присылать уведомления!

## 🏗️ Архитектура проекта

```
MarhrutochkaTG/
├── src/                    # Исходный код
│   ├── bot.py             # Основной бот
│   ├── parser.py          # Парсер сайта
│   └── __init__.py
├── docs/                   # Документация
│   ├── USER_GUIDE.md      # Руководство пользователя
│   ├── TESTING_GUIDE.md   # Тестирование
│   └── DEPLOYMENT.md      # Развертывание
├── tests/                  # Тесты
│   ├── test_all.py        # Полное тестирование
│   └── test_bot.py        # Тесты бота
├── scripts/                # Скрипты
│   ├── start_bot.sh       # Запуск бота
│   └── demo.py            # Демонстрация
├── main.py                 # Точка входа
├── requirements.txt        # Зависимости
├── .env.example           # Пример конфигурации
└── README.md              # Этот файл
```

## 🔧 Технологии

- **Python 3.8+** - основной язык
- **python-telegram-bot** - Telegram Bot API
- **aiohttp + BeautifulSoup** - парсинг сайта
- **APScheduler** - планирование задач
- **asyncio** - асинхронность

## 🧪 Тестирование

Запуск всех тестов:
```bash
source venv/bin/activate
python tests/test_all.py
```

Демонстрация парсера:
```bash
python scripts/demo.py
```

## 📱 Примеры использования

### Поиск рейсов:
```
Пользователь: 2025-07-15
Бот: 📅 Рейсы на 2025-07-15

🚌 Минск → Островец:
1. 07:00 → 09:25 (2ч 25м)
   ✅ 12 мест | Евротранспорт-Сервис
2. 07:30 → 09:55 (2ч 25м)
   ✅ 16 мест | Евротранспорт-Сервис
...
```

### Уведомление о найденных рейсах:
```
🔔 НАЙДЕНЫ ПОДХОДЯЩИЕ РЕЙСЫ!

📅 Дата: 2025-07-15
🛣️ Направление: Минск → Островец
⏰ Время: 07:00-09:00

1. Минск → Островец
🚀 07:30 → 🎯 09:55
✅ 5 мест | Евротранспорт-Сервис

🔄 Мониторинг продолжается...
```

## 📚 Документация

- [📖 Руководство пользователя](docs/USER_GUIDE.md)
- [🧪 Руководство по тестированию](docs/TESTING_GUIDE.md)
- [🚀 Развертывание](docs/DEPLOYMENT.md)

## 🐛 Troubleshooting

### Частые проблемы:

**Бот не запускается:**
- Проверьте токен в `.env`
- Убедитесь, что активировано виртуальное окружение
- Установите зависимости: `pip install -r requirements.txt`

**Не работает парсинг:**
- Сайт может быть временно недоступен
- Проверьте подключение к интернету
- Запустите тесты: `python tests/test_all.py`

**Не приходят уведомления:**
- Убедитесь, что мониторинг активен (`/monitoring`)
- Возможно, нет подходящих рейсов по критериям
- Попробуйте "📱 Проверить сейчас"

## 🤝 Участие в разработке

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Распространяется под лицензией MIT. См. [LICENSE](LICENSE) для подробностей.

## 👨‍💻 Автор

**OrDinaD** - [GitHub](https://github.com/OrDinaD)

## 🙏 Поддержка

Если проект помог вам, поставьте ⭐ на GitHub!

**Нашли баг?** Создайте [Issue](https://github.com/OrDinaD/MarhrutochkaTG/issues)  
**Есть идея?** Предложите [Feature Request](https://github.com/OrDinaD/MarhrutochkaTG/issues)

---

**📱 Найти бота:** [@MarshrutochkaOst_bot](https://t.me/MarshrutochkaOst_bot)  
**🌐 Источник данных:** [билет.маршруточка.бел](https://билет.маршруточка.бел)