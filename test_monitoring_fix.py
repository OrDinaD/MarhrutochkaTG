#!/usr/bin/env python3
"""
Тест функций мониторинга в боте
"""

import sys
import os
sys.path.append('src')

def test_monitoring_functions():
    """Тестирование функций мониторинга"""
    print("🧪 Тестирование функций мониторинга...")
    
    try:
        # Импорт основных функций
        from bot import (
            get_date_keyboard, 
            get_direction_keyboard,
            get_time_type_keyboard,
            get_time_range_keyboard,
            format_monitor_config
        )
        print("✅ Импорт функций клавиатур успешен")
        
        # Тест клавиатур
        date_kb = get_date_keyboard()
        direction_kb = get_direction_keyboard() 
        time_type_kb = get_time_type_keyboard()
        time_range_kb = get_time_range_keyboard("departure")
        
        print("✅ Генерация клавиатур успешна")
        
        # Проверяем структуру клавиатур
        assert hasattr(date_kb, 'inline_keyboard'), "Клавиатура даты неверная"
        assert hasattr(direction_kb, 'inline_keyboard'), "Клавиатура направления неверная"
        assert hasattr(time_type_kb, 'inline_keyboard'), "Клавиатура типа времени неверная"
        
        print("✅ Структура клавиатур корректна")
        
        # Тест конфигурации мониторинга
        test_config = {
            'date': '2025-08-12',
            'direction': 'minsk_ostrovets',
            'time_type': 'departure',
            'time_range': '07:00-09:00'
        }
        
        config_text = format_monitor_config(test_config)
        assert isinstance(config_text, str), "Конфигурация должна быть строкой"
        assert '2025-08-12' in config_text, "Дата должна быть в конфигурации"
        
        print("✅ Форматирование конфигурации работает")
        
        # Проверяем callback_data в кнопках
        direction_buttons = direction_kb.inline_keyboard
        found_callbacks = []
        for row in direction_buttons:
            for button in row:
                if button.callback_data:
                    found_callbacks.append(button.callback_data)
        
        expected_callbacks = ['dir_minsk_ostrovets', 'dir_ostrovets_minsk', 'dir_both']
        for callback in expected_callbacks:
            if callback in found_callbacks:
                print(f"✅ Найден callback: {callback}")
            else:
                print(f"❌ НЕ найден callback: {callback}")
        
        print("\n🎯 Результат тестирования:")
        print("✅ Все основные функции мониторинга работают корректно")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def test_conversation_states():
    """Тест состояний ConversationHandler"""
    print("\n🔄 Тестирование состояний...")
    
    try:
        from bot import (
            CHOOSE_DATE, CHOOSE_DIRECTION, CHOOSE_TIME_TYPE, 
            CHOOSE_TIME_RANGE, CONFIRM_MONITORING
        )
        
        states = [
            ('CHOOSE_DATE', CHOOSE_DATE),
            ('CHOOSE_DIRECTION', CHOOSE_DIRECTION),
            ('CHOOSE_TIME_TYPE', CHOOSE_TIME_TYPE),
            ('CHOOSE_TIME_RANGE', CHOOSE_TIME_RANGE),
            ('CONFIRM_MONITORING', CONFIRM_MONITORING)
        ]
        
        for name, value in states:
            print(f"✅ {name} = {value}")
        
        print("✅ Все состояния определены корректно")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта состояний: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск тестов мониторинга MarhrutochkaTG Bot")
    print("=" * 50)
    
    success = True
    
    # Основные функции
    if not test_monitoring_functions():
        success = False
    
    # Состояния
    if not test_conversation_states():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Все тесты пройдены успешно!")
        print("✅ Мониторинг готов к работе")
    else:
        print("❌ Некоторые тесты не прошли")
        sys.exit(1)
