# 🧪 План тестирования работы аккаунтов

## 📋 Оглавление
1. [Обзор системы](#обзор-системы)
2. [Текущее состояние](#текущее-состояние)
3. [Компоненты для тестирования](#компоненты-для-тестирования)
4. [План тестирования](#план-тестирования)
5. [Сценарии тестирования](#сценарии-тестирования)
6. [Рекомендации по улучшению](#рекомендации-по-улучшению)
7. [Чеклист перед продакшеном](#чеклист-перед-продакшеном)

---

## 🎯 Обзор системы

### Архитектура работы с аккаунтами

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Bot User                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              autobuy_handlers.py                             │
│  • account_menu() - управление аккаунтом                    │
│  • account_add_start() - добавление аккаунта                │
│  • autobuy_start() - запуск автопокупки                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              AccountManager                                  │
│  • add_account() - добавить/обновить аккаунт                │
│  • get_account() - получить учетные данные                  │
│  • has_account() - проверить наличие аккаунта               │
│  • remove_account() - удалить аккаунт                       │
│  • _encrypt()/_decrypt() - шифрование/дешифрование          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         data/user_accounts.json (зашифрованное хранилище)   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              TicketBuyer (Playwright)                        │
│  • login() - вход на сайт                                   │
│  • search_tickets() - поиск билетов                         │
│  • auto_buy_ticket() - автоматическая покупка               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Текущее состояние

### ✅ Реализовано

#### 1. **AccountManager** (`src/managers/account_manager.py`)
- ✅ Хранение учетных данных в JSON файле
- ✅ Простое XOR шифрование паролей
- ✅ CRUD операции для аккаунтов
- ✅ Статистика по аккаунтам

#### 2. **Handlers** (`src/autobuy_handlers.py`)
- ✅ ConversationHandler для добавления аккаунта
- ✅ ConversationHandler для автопокупки
- ✅ Валидация номера телефона
- ✅ Удаление сообщений с паролями
- ✅ Интеграция с AccountManager

#### 3. **TicketBuyer** (`src/utils/ticket_buyer.py`)
- ✅ Playwright для автоматизации браузера
- ✅ Асинхронный контекстный менеджер
- ✅ Обработка ошибок (AuthenticationError, BookingError)
- ✅ Логирование операций

#### 4. **Тесты** (`tests/test_autobuy.py`)
- ✅ Unit-тесты для AccountManager
- ✅ Unit-тесты для TicketBuyer
- ✅ Тесты шифрования/дешифрования
- ✅ Тесты персистентности данных

### ⚠️ Проблемы и риски

#### 🔴 Критические
1. **Слабое шифрование**
   - Используется простое XOR шифрование
   - Ключ по умолчанию в коде (`default_key_change_in_production`)
   - Не используется современная криптография (cryptography.fernet)

2. **Безопасность хранения**
   - Все данные в одном JSON файле
   - Нет ротации ключей
   - Нет соли для паролей

3. **Отсутствие валидации паролей**
   - Пароль сохраняется как есть
   - Нет проверки сложности

#### 🟡 Средние
1. **Playwright зависимости**
   - Требуется установка браузера
   - Большой размер зависимостей
   - Возможны проблемы в headless режиме

2. **Отсутствие тайм-аутов**
   - Нет ограничений на время операций
   - Возможны зависания

3. **Недостаточное логирование**
   - Не логируются все критические операции
   - Нет audit trail для действий с аккаунтами

#### 🟢 Низкие
1. **Нет Rate Limiting**
   - Пользователь может добавлять неограниченное количество аккаунтов
   - Нет защиты от спама

2. **UI/UX улучшения**
   - Можно добавить подтверждение перед удалением
   - Показывать замаскированный номер телефона

---

## 🧩 Компоненты для тестирования

### 1. AccountManager
**Файл:** `src/managers/account_manager.py`

**Методы:**
- `__init__(storage_file)` - инициализация
- `add_account(user_id, phone, password)` - добавление аккаунта
- `get_account(user_id)` - получение аккаунта
- `has_account(user_id)` - проверка наличия
- `remove_account(user_id)` - удаление аккаунта
- `get_stats()` - статистика
- `_encrypt(data)` - шифрование
- `_decrypt(encrypted_data)` - дешифрование
- `_load_accounts()` - загрузка из файла
- `_save_accounts()` - сохранение в файл

### 2. Autobuy Handlers
**Файл:** `src/autobuy_handlers.py`

**Функции:**
- `account_menu()` - меню управления
- `account_add_start()` - начало добавления
- `account_phone_received()` - получение номера
- `account_password_received()` - получение пароля
- `account_change()` - изменение аккаунта
- `autobuy_start()` - начало автопокупки
- `autobuy_confirm()` - подтверждение покупки

### 3. TicketBuyer
**Файл:** `src/utils/ticket_buyer.py`

**Методы:**
- `__init__(phone, password, headless)` - инициализация
- `start()` - запуск браузера
- `close()` - закрытие браузера
- `login()` - вход в аккаунт
- `check_authenticated()` - проверка авторизации
- `search_tickets()` - поиск билетов
- `auto_buy_ticket()` - автопокупка

---

## 📝 План тестирования

### Phase 1: Unit Testing (высокий приоритет)

#### 1.1 AccountManager - Базовые операции
- [ ] Тест создания нового экземпляра
- [ ] Тест добавления аккаунта
- [ ] Тест получения существующего аккаунта
- [ ] Тест получения несуществующего аккаунта
- [ ] Тест проверки наличия аккаунта
- [ ] Тест удаления аккаунта
- [ ] Тест обновления существующего аккаунта

#### 1.2 AccountManager - Шифрование
- [ ] Тест шифрования простой строки
- [ ] Тест дешифрования
- [ ] Тест шифрования/дешифрования круглого пути
- [ ] Тест с кириллицей
- [ ] Тест с спецсимволами
- [ ] Тест с пустой строкой
- [ ] Тест с очень длинной строкой (>1000 символов)

#### 1.3 AccountManager - Персистентность
- [ ] Тест сохранения в файл
- [ ] Тест загрузки из файла
- [ ] Тест сохранения между перезапусками
- [ ] Тест работы с поврежденным файлом
- [ ] Тест работы с несуществующим файлом
- [ ] Тест работы с недоступным для записи файлом

#### 1.4 AccountManager - Безопасность
- [ ] Тест использования кастомного ключа шифрования
- [ ] Тест что пароли не хранятся в plaintext
- [ ] Тест что данные в файле зашифрованы
- [ ] Тест корректной обработки ошибок дешифрования

#### 1.5 TicketBuyer - Базовая функциональность
- [ ] Тест инициализации
- [ ] Тест использования как контекстного менеджера
- [ ] Тест запуска браузера (мок)
- [ ] Тест закрытия браузера (мок)
- [ ] Тест обработки ошибок при запуске

#### 1.6 Handlers - Валидация
- [ ] Тест валидации номера телефона (9 цифр)
- [ ] Тест валидации номера телефона (неверный формат)
- [ ] Тест валидации даты
- [ ] Тест валидации времени

### Phase 2: Integration Testing (средний приоритет)

#### 2.1 AccountManager + TicketBuyer
- [ ] Тест получения учетных данных и передачи в TicketBuyer
- [ ] Тест работы с несуществующим аккаунтом
- [ ] Тест работы с неверными учетными данными

#### 2.2 Handlers + AccountManager
- [ ] Тест полного потока добавления аккаунта
- [ ] Тест отмены добавления аккаунта
- [ ] Тест изменения существующего аккаунта
- [ ] Тест запуска автопокупки без аккаунта
- [ ] Тест запуска автопокупки с аккаунтом

#### 2.3 End-to-End (с моками)
- [ ] Тест полного цикла: добавление аккаунта → автопокупка (мок)
- [ ] Тест обработки ошибки авторизации
- [ ] Тест обработки ошибки бронирования
- [ ] Тест отмены операции

### Phase 3: Manual Testing (критический для продакшена)

#### 3.1 Функциональное тестирование
- [ ] Добавить аккаунт через бота
- [ ] Проверить что аккаунт сохранился
- [ ] Проверить меню управления аккаунтом
- [ ] Изменить аккаунт
- [ ] Удалить аккаунт (если функция есть)
- [ ] Попробовать добавить аккаунт с неверным номером
- [ ] Попробовать автопокупку без аккаунта
- [ ] Попробовать автопокупку с аккаунтом

#### 3.2 Тестирование с реальным сайтом (осторожно!)
- [ ] Тест входа с правильными учетными данными
- [ ] Тест входа с неправильными учетными данными
- [ ] Тест поиска билетов
- [ ] ⚠️ Тест бронирования (НЕ покупки!) билета
- [ ] Проверить что сообщения с паролем удаляются

#### 3.3 Безопасность
- [ ] Проверить файл user_accounts.json - пароли должны быть зашифрованы
- [ ] Проверить что установлена переменная ENCRYPTION_KEY
- [ ] Проверить что файл недоступен посторонним (права доступа)
- [ ] Проверить логи - пароли не должны попадать в логи

#### 3.4 Производительность
- [ ] Время добавления аккаунта < 1 сек
- [ ] Время получения аккаунта < 100 мс
- [ ] Размер файла при 10/100/1000 аккаунтов
- [ ] Запуск браузера < 5 сек
- [ ] Вход в аккаунт < 10 сек

### Phase 4: Stress Testing (низкий приоритет)

- [ ] Добавление 1000 аккаунтов
- [ ] Параллельные операции с AccountManager
- [ ] Долгая работа TicketBuyer (30+ минут)
- [ ] Восстановление после сбоя
- [ ] Работа при низкой скорости интернета

---

## 🎬 Сценарии тестирования

### Сценарий 1: Первое использование
**Цель:** Проверить что новый пользователь может добавить аккаунт

**Шаги:**
1. Отправить `/account` боту
2. Нажать "➕ Добавить аккаунт"
3. Ввести номер телефона: `299605390`
4. Ввести пароль: `test_password_123`
5. Проверить сообщение "✅ Аккаунт успешно добавлен!"

**Ожидаемый результат:**
- Аккаунт добавлен в систему
- Данные зашифрованы в файле
- Сообщение с паролем удалено

**Проверка:**
```bash
# Проверить что файл создан
ls -la data/user_accounts.json

# Проверить что данные зашифрованы (не должен быть plaintext пароль)
cat data/user_accounts.json | grep "test_password_123"
# Должен вернуть пустой результат
```

---

### Сценарий 2: Автопокупка без аккаунта
**Цель:** Проверить корректную обработку попытки автопокупки без аккаунта

**Шаги:**
1. Отправить `/autobuy` боту
2. Проверить сообщение "⚠️ Аккаунт не подключен"
3. Должна быть кнопка "➕ Добавить аккаунт"

**Ожидаемый результат:**
- Пользователь получает понятное сообщение
- Есть возможность сразу добавить аккаунт

---

### Сценарий 3: Успешная автопокупка
**Цель:** Проверить полный цикл автопокупки

**⚠️ ВНИМАНИЕ:** Этот тест может привести к реальной покупке билета!

**Подготовка:**
1. Создать тестовый аккаунт на сайте маршруток
2. Пополнить баланс минимальной суммой (если требуется)

**Шаги:**
1. Добавить аккаунт через `/account`
2. Отправить `/autobuy`
3. Ввести город отправления: `Минск`
4. Ввести город назначения: `Островец`
5. Ввести дату: `2025-12-01` (будущая дата)
6. Ввести время: `-` (пропустить)
7. Нажать "✅ Купить"
8. Дождаться результата

**Ожидаемый результат:**
- Бот находит доступные билеты
- Бот успешно входит в аккаунт
- Бот бронирует/покупает билет
- Пользователь получает детали билета

**Проверка:**
```bash
# Проверить логи
tail -f logs/bot.log | grep "autobuy"

# Проверить на сайте в "Мои билеты"
```

---

### Сценарий 4: Неверные учетные данные
**Цель:** Проверить обработку ошибки авторизации

**Шаги:**
1. Добавить аккаунт с неверным паролем
2. Попробовать автопокупку
3. Проверить сообщение об ошибке

**Ожидаемый результат:**
- "❌ Ошибка авторизации"
- Предложение проверить учетные данные

---

### Сценарий 5: Изменение аккаунта
**Цель:** Проверить обновление учетных данных

**Шаги:**
1. Добавить аккаунт
2. Отправить `/account`
3. Нажать "🔄 Изменить аккаунт"
4. Ввести новые данные
5. Попробовать автопокупку

**Ожидаемый результат:**
- Старые данные заменены
- Автопокупка работает с новыми данными

---

### Сценарий 6: Одновременные операции
**Цель:** Проверить работу с несколькими пользователями

**Шаги:**
1. Два пользователя одновременно добавляют аккаунты
2. Два пользователя одновременно запускают автопокупку
3. Проверить что данные не смешиваются

**Ожидаемый результат:**
- Каждый пользователь работает со своим аккаунтом
- Нет конфликтов записи в файл

---

## 🔧 Рекомендации по улучшению

### 🔴 Критические (сделать перед продакшеном)

#### 1. Улучшить шифрование
**Проблема:** XOR шифрование легко взламывается

**Решение:**
```python
from cryptography.fernet import Fernet

class AccountManager:
    def __init__(self):
        # Генерировать или загружать ключ из переменной окружения
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY must be set!")
        self.cipher = Fernet(key.encode())
    
    def _encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

**Миграция:**
1. Создать скрипт миграции старых данных
2. Установить `cryptography`: `pip install cryptography`
3. Сгенерировать новый ключ: `Fernet.generate_key()`
4. Установить в переменную окружения
5. Перешифровать все существующие аккаунты

#### 2. Добавить ENCRYPTION_KEY в .env
**Файл:** `.env.example`
```bash
# Для шифрования паролей аккаунтов
ENCRYPTION_KEY=your-fernet-key-here-generate-with-Fernet.generate_key()
```

**Генерация ключа:**
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

#### 3. Добавить валидацию ключа при старте
**Файл:** `src/managers/account_manager.py`
```python
def __init__(self, storage_file: str = "data/user_accounts.json"):
    if not os.getenv('ENCRYPTION_KEY'):
        logger.critical("ENCRYPTION_KEY not set! Cannot start.")
        raise ValueError("ENCRYPTION_KEY environment variable must be set")
    # ...
```

#### 4. Добавить права доступа к файлу
```python
def _save_accounts(self):
    with open(self.storage_file, 'w', encoding='utf-8') as f:
        json.dump(self.accounts, f, ensure_ascii=False, indent=2)
    
    # Установить права только для владельца
    os.chmod(self.storage_file, 0o600)
    logger.info("Аккаунты сохранены с безопасными правами")
```

### 🟡 Важные (желательно сделать)

#### 5. Добавить подтверждение удаления аккаунта
```python
async def account_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления аккаунта"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data="account_remove_yes"),
            InlineKeyboardButton("❌ Отмена", callback_data="account_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "⚠️ <b>Удаление аккаунта</b>\n\n"
        "Вы уверены, что хотите удалить сохраненный аккаунт?\n"
        "Это действие нельзя отменить.",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
```

#### 6. Показывать замаскированный номер
```python
def mask_phone(phone: str) -> str:
    """Маскирует номер телефона: 299605390 -> 29***5390"""
    if len(phone) < 4:
        return phone
    return f"{phone[:2]}***{phone[-4:]}"

# Использование
masked = mask_phone(account['phone'])
text += f"📱 Номер: <code>{masked}</code>\n"
```

#### 7. Добавить лимит аккаунтов на пользователя
```python
MAX_ACCOUNTS_PER_USER = 1  # Один аккаунт на пользователя

def add_account(self, user_id: int, phone: str, password: str) -> bool:
    if user_id in self.accounts:
        # Обновление существующего
        logger.info(f"Обновление аккаунта для пользователя {user_id}")
    else:
        # Проверка лимита
        if len(self.accounts) >= MAX_ACCOUNTS_PER_USER * 1000:  # Например, макс 1000 пользователей
            logger.warning("Достигнут лимит аккаунтов в системе")
            return False
    # ...
```

#### 8. Логировать действия с аккаунтами (audit trail)
```python
import datetime

def _log_action(self, action: str, user_id: int, success: bool):
    """Логировать действия для аудита"""
    log_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'action': action,
        'user_id': user_id,
        'success': success
    }
    
    # Сохранить в отдельный лог файл
    with open('data/account_audit.log', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

def add_account(self, user_id: int, phone: str, password: str) -> bool:
    try:
        # ... код добавления ...
        self._log_action('add_account', user_id, True)
        return True
    except Exception as e:
        self._log_action('add_account', user_id, False)
        return False
```

### 🟢 Nice-to-have (улучшения UX)

#### 9. Добавить тест аккаунта
```python
async def account_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестировать аккаунт без покупки"""
    await update.callback_query.answer()
    user_id = update.effective_user.id
    
    account = account_manager.get_account(user_id)
    if not account:
        await update.callback_query.edit_message_text("❌ Аккаунт не найден")
        return
    
    await update.callback_query.edit_message_text(
        "⏳ Проверяю аккаунт...\n"
        "Попытка входа на сайт..."
    )
    
    try:
        async with TicketBuyer(account['phone'], account['password'], headless=True) as buyer:
            result = await buyer.login()
            
            if result:
                await update.callback_query.edit_message_text(
                    "✅ <b>Аккаунт работает!</b>\n\n"
                    "Вход на сайт выполнен успешно.\n"
                    "Можете использовать автопокупку.",
                    parse_mode='HTML'
                )
            else:
                await update.callback_query.edit_message_text(
                    "❌ <b>Ошибка входа</b>\n\n"
                    "Не удалось войти с этими учетными данными.\n"
                    "Проверьте правильность номера и пароля.",
                    parse_mode='HTML'
                )
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"❌ Ошибка при тестировании: {str(e)}"
        )
```

#### 10. Добавить историю автопокупок
```python
class PurchaseHistory:
    """История покупок пользователя"""
    
    def __init__(self):
        self.history_file = Path("data/purchase_history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
    
    def add_purchase(self, user_id: int, purchase_info: dict):
        """Добавить запись о покупке"""
        purchase_info['timestamp'] = datetime.now().isoformat()
        purchase_info['user_id'] = user_id
        
        # Загрузить существующую историю
        history = self._load_history()
        
        if user_id not in history:
            history[user_id] = []
        
        history[user_id].append(purchase_info)
        
        # Сохранить
        with open(self.history_file, 'w') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def get_user_history(self, user_id: int) -> List[dict]:
        """Получить историю покупок пользователя"""
        history = self._load_history()
        return history.get(user_id, [])
```

---

## ✅ Чеклист перед продакшеном

### Безопасность
- [ ] ENCRYPTION_KEY установлен и не содержит значение по умолчанию
- [ ] Используется cryptography.Fernet вместо XOR
- [ ] Файл user_accounts.json имеет права 600 (только владелец)
- [ ] Пароли не попадают в логи
- [ ] Сообщения с паролями удаляются сразу после получения
- [ ] Audit log для всех действий с аккаунтами

### Функциональность
- [ ] Все unit-тесты проходят (pytest tests/test_autobuy.py)
- [ ] Ручное тестирование добавления аккаунта пройдено
- [ ] Ручное тестирование автопокупки пройдено (осторожно!)
- [ ] Тестирование с неверными учетными данными пройдено
- [ ] Playwright установлен и работает (playwright install)
- [ ] Браузер запускается в headless режиме

### Производительность
- [ ] Время добавления аккаунта < 1 секунды
- [ ] Время запуска браузера < 5 секунд
- [ ] Нет утечек памяти при долгой работе
- [ ] Файл user_accounts.json не растет бесконечно

### Документация
- [ ] README.md обновлен с инструкциями по аккаунтам
- [ ] .env.example содержит ENCRYPTION_KEY
- [ ] Инструкция по генерации ключа шифрования
- [ ] Документация по тестированию актуальна

### Deployment
- [ ] Railway/Heroku переменная ENCRYPTION_KEY установлена
- [ ] Playwright установлен в production (buildpack)
- [ ] Директория data/ существует и доступна для записи
- [ ] Логи настроены корректно

### Мониторинг
- [ ] Алерты на ошибки авторизации
- [ ] Алерты на ошибки бронирования
- [ ] Метрики использования автопокупки
- [ ] Логирование всех критических операций

---

## 🚀 Быстрый старт тестирования

### 1. Подготовка окружения

```bash
# Клонировать репозиторий
git clone https://github.com/OrDinaD/MarhrutochkaTG.git
cd MarhrutochkaTG

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
pip install -r requirements.dev.txt

# Установить Playwright браузеры
playwright install chromium

# Создать .env файл
cp .env.example .env
# Отредактировать .env и добавить:
# - TELEGRAM_BOT_TOKEN
# - ADMIN_TELEGRAM_ID
# - ENCRYPTION_KEY (сгенерировать новый!)
```

### 2. Генерация ключа шифрования

```python
# Запустить Python и выполнить:
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
# Скопировать ключ в .env как ENCRYPTION_KEY
```

### 3. Запуск unit-тестов

```bash
# Все тесты
pytest tests/test_autobuy.py -v

# Только тесты AccountManager
pytest tests/test_autobuy.py::TestAccountManager -v

# С покрытием
pytest tests/test_autobuy.py --cov=src.managers.account_manager --cov-report=html
```

### 4. Ручное тестирование

```bash
# Запустить бота
python main.py

# В Telegram:
# 1. Отправить /account боту
# 2. Добавить тестовый аккаунт
# 3. Проверить что данные сохранились
# 4. Попробовать /autobuy (осторожно с реальными покупками!)
```

### 5. Проверка безопасности

```bash
# Проверить что пароли зашифрованы
cat data/user_accounts.json
# Не должно быть plaintext паролей!

# Проверить права доступа
ls -la data/user_accounts.json
# Должно быть -rw------- (600)

# Проверить что ключ установлен
echo $ENCRYPTION_KEY
# Должен быть установлен и не равен default_key_change_in_production
```

---

## 📞 Поддержка и помощь

### Если что-то не работает:

1. **Проверить логи:**
   ```bash
   tail -f logs/bot.log
   ```

2. **Проверить переменные окружения:**
   ```bash
   env | grep -E "TELEGRAM|ENCRYPTION"
   ```

3. **Проверить Playwright:**
   ```bash
   playwright --version
   playwright install --dry-run chromium
   ```

4. **Проверить тесты:**
   ```bash
   pytest tests/test_autobuy.py --tb=short
   ```

5. **Включить debug логи:**
   ```python
   # В main.py
   logging.basicConfig(level=logging.DEBUG)
   ```

---

## 📚 Дополнительные ресурсы

- [Playwright Documentation](https://playwright.dev/python/)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [Cryptography Documentation](https://cryptography.io/)
- [pytest Documentation](https://docs.pytest.org/)

---

**Версия документа:** 1.0  
**Дата создания:** 2025-11-16  
**Автор:** GitHub Copilot Agent  
**Статус:** ✅ Готово к использованию
