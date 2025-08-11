#!/usr/bin/env python3
"""
Скрипт для интеграции модуля безопасности в bot.py
"""

import re

def integrate_security_into_bot():
    """Интегрирует модуль безопасности в основной код бота"""
    
    # Читаем текущий bot.py
    with open('/Users/vlad/Developer/Marha/src/bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Добавляем импорт безопасности (если его нет)
    if 'from .security import security' not in content and 'from security import security' not in content:
        # Находим место после других импортов
        import_pattern = r'(from \.admin_panel import AdminPanel)'
        replacement = r'\1\ntry:\n    from .security import security\nexcept ImportError:\n    from security import security'
        content = re.sub(import_pattern, replacement, content)
    
    # Добавляем валидацию в функцию обработки телефона
    phone_pattern = r'(async def handle_phone_requests\(.*?\):.*?phone = update\.message\.text\.strip\(\))(.*?)(context\.user_data\[\'phone\'\] = phone)'
    
    def phone_replacement(match):
        func_start = match.group(1)
        middle_content = match.group(2)
        context_line = match.group(3)
        
        new_content = f"""{func_start}
    
    # Валидация номера телефона
    if not security.validate_phone(phone):
        security.log_security_event("invalid_phone", update.effective_user.id, {{"phone": phone}})
        await update.message.reply_text(
            "❌ **Неверный формат номера телефона**\\n\\n"
            "📱 Используйте формат:\\n"
            "• +375XXXXXXXXX\\n"
            "• 375XXXXXXXXX\\n\\n"
            "💡 Пример: +375291234567",
            parse_mode='Markdown'
        )
        return LOGIN_REQUESTS_PHONE
    
    # Санитизация номера
    clean_phone = security.sanitize_input(phone, max_length=20){middle_content}
    context.user_data['phone'] = clean_phone"""
        
        return new_content
    
    content = re.sub(phone_pattern, phone_replacement, content, flags=re.DOTALL)
    
    # Добавляем валидацию дат в функции выбора даты
    date_pattern = r'(if data\.startswith\("date_"\):.*?date = data\.replace\("date_", ""\))'
    
    def date_replacement(match):
        original = match.group(1)
        return f"""{original}
        
        # Валидация даты
        if not security.validate_date(date):
            security.log_security_event("invalid_date", user_id, {{"date": date}})
            await query.edit_message_text(
                "❌ **Неверный формат даты**\\n\\n"
                "📅 Используйте формат YYYY-MM-DD\\n"
                "💡 Пример: 2025-01-15",
                parse_mode='Markdown'
            )
            return CHOOSE_DATE"""
    
    content = re.sub(date_pattern, date_replacement, content, flags=re.DOTALL)
    
    # Сохраняем измененный файл
    with open('/Users/vlad/Developer/Marha/src/bot_with_security.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Создан файл bot_with_security.py с интегрированной безопасностью")
    print("📝 Для применения изменений переименуйте его в bot.py")

if __name__ == "__main__":
    integrate_security_into_bot()
