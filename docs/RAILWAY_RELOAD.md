# Настройка команды /reload для Railway

Команда `/reload` позволяет администратору перезагрузить бота прямо из Telegram, используя Railway API.

## Необходимые переменные окружения

Добавьте эти переменные в настройках вашего Railway проекта:

### 1. RAILWAY_TOKEN

Railway API токен для доступа к GraphQL API.

**Как получить:**
1. Перейдите на https://railway.app/account/tokens
2. Нажмите "Create Token"
3. Дайте токену имя (например, "Bot Reload Token")
4. Скопируйте созданный токен
5. Добавьте в Railway: `RAILWAY_TOKEN=your_token_here`

### 2. RAILWAY_SERVICE_ID

ID сервиса вашего бота на Railway.

**Как получить:**

Вариант 1 - Через Railway CLI:
```bash
railway status
```

Вариант 2 - Через URL:
Откройте ваш проект в Railway, ID сервиса будет в URL:
```
https://railway.app/project/[PROJECT_ID]/service/[SERVICE_ID]
                                                    ^^^^^^^^^^^
```

Вариант 3 - Через скрипт:
```bash
cd scripts
./get_railway_service_id.sh
```

Добавьте в Railway: `RAILWAY_SERVICE_ID=your_service_id_here`

### 3. ADMIN_TELEGRAM_ID

ID администратора Telegram (должен быть уже настроен).

**Проверка:**
```bash
echo $ADMIN_TELEGRAM_ID
```

Если не установлен, добавьте ваш Telegram ID.

## Использование

После настройки переменных окружения:

1. Перезапустите бота на Railway чтобы подхватились новые переменные
2. Отправьте команду `/reload` в Telegram
3. Бот отправит запрос на Railway API для перезагрузки
4. Через 30-60 секунд бот будет перезапущен

## Безопасность

- Команда доступна **только администратору** (проверка по ADMIN_TELEGRAM_ID)
- Railway токен хранится в переменных окружения и не логируется
- Все действия логируются в систему мониторинга

## Troubleshooting

### Ошибка: "Не найдены переменные окружения"
- Убедитесь что RAILWAY_TOKEN и RAILWAY_SERVICE_ID добавлены в Railway
- Перезапустите бота после добавления переменных

### Ошибка: "У вас нет прав"
- Проверьте что ваш Telegram ID совпадает с ADMIN_TELEGRAM_ID
- Получить свой ID можно через бота @userinfobot

### Ошибка Railway API
- Проверьте что токен валиден и не истек
- Проверьте что SERVICE_ID правильный
- Проверьте логи Railway для деталей

### Таймаут запроса
- Railway API может быть недоступен временно
- Попробуйте позже
- Проверьте статус Railway: https://status.railway.app/
