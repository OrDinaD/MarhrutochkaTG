#!/usr/bin/env python3
"""
Тест админ-панели
"""

from src.admin_panel import AdminPanel

def test_admin():
    print('=== Тест админ-панели ===')
    
    # Создаем админ-панель
    admin_panel = AdminPanel(599050881)  # ID из .env
    
    print(f'Админ ID: {admin_panel.admin_telegram_id}')
    print(f'Проверка админа (599050881): {admin_panel.is_admin(599050881)}')
    print(f'Проверка обычного пользователя (123456): {admin_panel.is_admin(123456)}')
    
    # Тест клавиатуры админа
    keyboard = admin_panel.get_admin_menu_keyboard()
    print(f'Кнопок в админ-меню: {len(keyboard.inline_keyboard)}')
    
    for row in keyboard.inline_keyboard:
        for button in row:
            print(f'  - {button.text} ({button.callback_data})')
    
    print('✅ Тесты админ-панели завершены')

if __name__ == "__main__":
    test_admin()
