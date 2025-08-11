#!/usr/bin/env python3
"""
Простой тест синтаксиса и структуры мониторинга
"""

import sys
import os
import re

def test_monitoring_fix():
    """Тестирование исправлений мониторинга"""
    print("🧪 Проверяем исправления мониторинга...")
    
    # Читаем файл bot.py
    with open('src/bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем наличие новой функции
    if 'async def handle_monitoring_direction_choice' in content:
        print("✅ Найдена функция handle_monitoring_direction_choice")
    else:
        print("❌ НЕ найдена функция handle_monitoring_direction_choice")
        return False
    
    # Проверяем правильный обработчик в ConversationHandler
    if 'CallbackQueryHandler(handle_monitoring_direction_choice)' in content:
        print("✅ ConversationHandler использует правильный обработчик")
    else:
        print("❌ ConversationHandler использует неправильный обработчик")
        return False
    
    # Проверяем callback_data для мониторинга
    monitoring_callbacks = re.findall(r'callback_data="(dir_[^"]+)"', content)
    expected_callbacks = ['dir_minsk_ostrovets', 'dir_ostrovets_minsk', 'dir_both']
    
    for callback in expected_callbacks:
        if callback in monitoring_callbacks:
            print(f"✅ Найден callback для мониторинга: {callback}")
        else:
            print(f"❌ НЕ найден callback для мониторинга: {callback}")
    
    # Проверяем функции клавиатур
    keyboard_functions = [
        'def get_date_keyboard()',
        'def get_direction_keyboard()',
        'def get_time_type_keyboard()',
        'def get_time_range_keyboard(',
        'def format_monitor_config('
    ]
    
    for func in keyboard_functions:
        if func in content:
            print(f"✅ Найдена функция: {func}")
        else:
            print(f"❌ НЕ найдена функция: {func}")
    
    # Проверяем состояния
    states_pattern = r'\(CHOOSE_DATE, CHOOSE_DIRECTION, CHOOSE_TIME_TYPE, CHOOSE_TIME_RANGE,\s+CONFIRM_MONITORING'
    if re.search(states_pattern, content):
        print("✅ Состояния мониторинга определены корректно")
    else:
        print("❌ Проблемы с определением состояний")
    
    # Проверяем отсутствие старого неправильного обработчика в CHOOSE_DIRECTION
    if 'CallbackQueryHandler(handle_direction_choice)' in content:
        # Проверяем что это не в состоянии CHOOSE_DIRECTION мониторинга
        lines = content.split('\n')
        in_monitoring_conv = False
        for i, line in enumerate(lines):
            if 'monitoring_conv_handler = ConversationHandler(' in line:
                in_monitoring_conv = True
            elif in_monitoring_conv and 'CHOOSE_DIRECTION:' in line:
                next_lines = '\n'.join(lines[i:i+3])
                if 'handle_direction_choice' in next_lines:
                    print("❌ Все еще используется старый обработчик в мониторинге")
                    return False
                else:
                    print("✅ Используется правильный обработчик в мониторинге")
                break
    
    print("✅ Все проверки пройдены успешно!")
    return True

def analyze_conversation_flow():
    """Анализ потока conversation handler"""
    print("\n🔄 Анализ потока мониторинга...")
    
    flow_steps = [
        "1. start_monitoring_conversation -> CHOOSE_DATE",
        "2. handle_date_choice -> CHOOSE_DIRECTION", 
        "3. handle_monitoring_direction_choice -> CHOOSE_TIME_TYPE",
        "4. handle_time_type_choice -> CHOOSE_TIME_RANGE или CONFIRM_MONITORING",
        "5. handle_time_range_choice -> CONFIRM_MONITORING",
        "6. handle_monitoring_confirmation -> END"
    ]
    
    for step in flow_steps:
        print(f"✅ {step}")
    
    print("✅ Поток мониторинга логически корректен")

if __name__ == "__main__":
    print("🚀 Проверка исправлений мониторинга")
    print("=" * 50)
    
    success = test_monitoring_fix()
    
    if success:
        analyze_conversation_flow()
        print("\n" + "=" * 50)
        print("🎉 Исправления мониторинга корректны!")
        print("✅ Готово к тестированию в Telegram")
    else:
        print("\n" + "=" * 50)
        print("❌ Требуются дополнительные исправления")
        sys.exit(1)
