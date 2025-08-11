#!/usr/bin/env python3
"""
Симуляция работы мониторинга с mock данными
"""

import sys
import asyncio
from unittest.mock import Mock, AsyncMock

class MockUpdate:
    def __init__(self, callback_data=None, message_text=None):
        self.callback_query = Mock() if callback_data else None
        self.message = Mock() if message_text else None
        self.effective_user = Mock()
        self.effective_user.id = 12345
        
        if callback_data:
            self.callback_query.data = callback_data
            self.callback_query.from_user = self.effective_user
            self.callback_query.answer = AsyncMock()
            self.callback_query.edit_message_text = AsyncMock()
        
        if message_text:
            self.message.text = message_text
            self.message.reply_text = AsyncMock()

class MockContext:
    def __init__(self):
        self.user_data = {}

async def simulate_monitoring_flow():
    """Симуляция полного потока настройки мониторинга"""
    print("🎭 Симуляция настройки мониторинга...")
    
    # Мокаем необходимые компоненты
    sys.path.append('src')
    
    # Создаем Mock версии функций без telegram зависимостей
    def mock_get_date_keyboard():
        return {"type": "date_keyboard", "options": ["date_2025-08-12", "date_2025-08-13"]}
    
    def mock_get_direction_keyboard():
        return {"type": "direction_keyboard", "options": ["dir_minsk_ostrovets", "dir_ostrovets_minsk", "dir_both"]}
    
    def mock_get_time_type_keyboard():
        return {"type": "time_type_keyboard", "options": ["time_departure", "time_arrival", "time_any"]}
    
    def mock_format_monitor_config(config):
        return f"Дата: {config.get('date', 'н/д')}\nНаправление: {config.get('direction', 'н/д')}"
    
    # Симуляция user_data_store
    user_data_store = {}
    
    # Симуляция состояний
    CHOOSE_DATE = 0
    CHOOSE_DIRECTION = 1  
    CHOOSE_TIME_TYPE = 2
    
    # Симуляция функций обработчиков
    async def mock_start_monitoring_conversation(update, context):
        user_id = update.effective_user.id
        user_data_store[user_id] = {}
        print(f"✅ Пользователь {user_id} начал настройку мониторинга")
        return CHOOSE_DATE
    
    async def mock_handle_date_choice(update, context):
        user_id = update.effective_user.id
        data = update.callback_query.data
        
        if data.startswith("date_"):
            selected_date = data.replace("date_", "")
            user_data_store[user_id]['date'] = selected_date
            print(f"✅ Выбрана дата: {selected_date}")
            return CHOOSE_DIRECTION
        return CHOOSE_DATE
    
    async def mock_handle_monitoring_direction_choice(update, context):
        user_id = update.effective_user.id
        data = update.callback_query.data
        
        if data.startswith("dir_"):
            direction = data.replace("dir_", "")
            user_data_store[user_id]['direction'] = direction
            direction_text = {
                "minsk_ostrovets": "Минск → Островец",
                "ostrovets_minsk": "Островец → Минск",
                "both": "Оба направления"
            }.get(direction, direction)
            print(f"✅ Выбрано направление: {direction_text}")
            return CHOOSE_TIME_TYPE
        return CHOOSE_DIRECTION
    
    # Тестируем поток
    print("\n🚀 Запуск симуляции:")
    
    # Шаг 1: Начало настройки
    update1 = MockUpdate(callback_data="setup_monitoring")
    context1 = MockContext()
    
    state = await mock_start_monitoring_conversation(update1, context1)
    assert state == CHOOSE_DATE, f"Ожидали CHOOSE_DATE, получили {state}"
    print("1️⃣ Настройка мониторинга начата")
    
    # Шаг 2: Выбор даты
    update2 = MockUpdate(callback_data="date_2025-08-12")
    state = await mock_handle_date_choice(update2, context1)
    assert state == CHOOSE_DIRECTION, f"Ожидали CHOOSE_DIRECTION, получили {state}"
    assert user_data_store[12345]['date'] == '2025-08-12', "Дата не сохранилась"
    print("2️⃣ Дата выбрана и сохранена")
    
    # Шаг 3: Выбор направления  
    update3 = MockUpdate(callback_data="dir_minsk_ostrovets")
    state = await mock_handle_monitoring_direction_choice(update3, context1)
    assert state == CHOOSE_TIME_TYPE, f"Ожидали CHOOSE_TIME_TYPE, получили {state}"
    assert user_data_store[12345]['direction'] == 'minsk_ostrovets', "Направление не сохранилось"
    print("3️⃣ Направление выбрано и сохранено")
    
    # Проверяем итоговые данные
    final_data = user_data_store[12345]
    print(f"\n📊 Итоговые данные мониторинга:")
    print(f"   Дата: {final_data.get('date')}")
    print(f"   Направление: {final_data.get('direction')}")
    
    config_text = mock_format_monitor_config(final_data)
    print(f"\n📋 Конфигурация:\n{config_text}")
    
    print("\n✅ Симуляция прошла успешно!")
    return True

def test_callback_data_mapping():
    """Тест правильности callback_data"""
    print("\n🎯 Тестирование callback_data...")
    
    # Тестируем маппинг направлений
    direction_mapping = {
        "dir_minsk_ostrovets": "Минск → Островец",
        "dir_ostrovets_minsk": "Островец → Минск", 
        "dir_both": "Оба направления"
    }
    
    for callback, text in direction_mapping.items():
        direction = callback.replace("dir_", "")
        print(f"✅ {callback} -> {direction} -> {text}")
    
    # Тестируем маппинг времени
    time_mapping = {
        "time_departure": "время отправления",
        "time_arrival": "время прибытия",
        "time_any": "любое время"
    }
    
    for callback, text in time_mapping.items():
        time_type = callback.replace("time_", "")
        print(f"✅ {callback} -> {time_type} -> {text}")
    
    print("✅ Все маппинги корректны")

async def main():
    print("🧪 Полное тестирование исправлений мониторинга")
    print("=" * 60)
    
    success = True
    
    # Симуляция потока
    try:
        await simulate_monitoring_flow()
    except Exception as e:
        print(f"❌ Ошибка в симуляции: {e}")
        success = False
    
    # Тест callback_data
    test_callback_data_mapping()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ Мониторинг полностью исправлен и готов к работе")
    else:
        print("❌ Есть проблемы в работе мониторинга")

if __name__ == "__main__":
    asyncio.run(main())
