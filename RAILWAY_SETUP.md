# 🚂 Railway Deployment Setup

## Настройка GitHub Secrets

Для корректной работы автоматического развертывания на Railway, необходимо настроить следующие секреты в вашем GitHub репозитории:

### Обязательные секреты:

1. **RAILWAY_TOKEN** - токен проекта Railway
   - Перейдите в Railway Dashboard
   - Откройте ваш проект
   - Перейдите в Settings → Tokens
   - Создайте новый Project Token
   - Скопируйте токен и добавьте его в GitHub Secrets

### Как добавить секреты в GitHub:

1. Откройте ваш репозиторий на GitHub
2. Перейдите в Settings → Secrets and variables → Actions
3. Нажмите "New repository secret"
4. Введите имя секрета и значение
5. Нажмите "Add secret"

## Как работает деплой

1. **Автоматический триггер**: деплой запускается при push в ветку `main` или создании тега
2. **Аутентификация**: используется RAILWAY_TOKEN без необходимости интерактивного входа
3. **Команда деплоя**: `railway up --detach` - развертывание в фоновом режиме

## Устранение неполадок

### Ошибка "Cannot login in non-interactive mode"
Эта ошибка была исправлена - больше не используется команда `railway login --browserless`. 
Вместо этого Railway CLI автоматически использует переменную окружения RAILWAY_TOKEN.

### Ошибка "RAILWAY_TOKEN is not set"
1. Убедитесь, что вы добавили RAILWAY_TOKEN в GitHub Secrets
2. Проверьте, что токен действителен и имеет права на развертывание проекта
3. Убедитесь, что имя секрета написано правильно (RAILWAY_TOKEN)

## Дополнительная информация

- [Railway CLI Documentation](https://docs.railway.app/reference/cli-api)
- [GitHub Actions с Railway](https://docs.railway.app/tutorials/github-actions)
- [Railway Project Tokens](https://docs.railway.app/reference/tokens)
