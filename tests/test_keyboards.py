#!/usr/bin/env python3
"""
Тесты для фабрики клавиатур
"""

import pytest
from datetime import datetime, timedelta
from utils.keyboards import KeyboardFactory


class TestKeyboardFactory:
    """Тесты фабрики клавиатур"""
    
    def test_get_main_menu_keyboard_user(self):
        """Тест главного меню для обычного пользователя"""
        keyboard = KeyboardFactory.get_main_menu_keyboard(user_id=12345, is_admin=False)
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
        
        # Проверяем основные кнопки
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "🔍 Поиск рейсов" in buttons_text
        assert "🔔 Настроить мониторинг" in buttons_text
        assert "📊 Мои мониторинги" in buttons_text
        assert "🌐 Открыть сайт" in buttons_text
        
        # Админ-панель не должна быть доступна
        assert "⚙️ Админ-панель" not in buttons_text
    
    def test_get_main_menu_keyboard_admin(self):
        """Тест главного меню для администратора"""
        keyboard = KeyboardFactory.get_main_menu_keyboard(user_id=12345, is_admin=True)
        
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        
        # Админ-панель должна быть доступна
        assert "⚙️ Админ-панель" in buttons_text
    
    def test_get_date_keyboard_default(self):
        """Тест клавиатуры выбора даты по умолчанию"""
        keyboard = KeyboardFactory.get_date_keyboard()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) >= 7  # 7 дней + доп. кнопки
        
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        
        # Проверяем наличие сегодня и завтра
        assert any("Сегодня" in btn for btn in buttons_text)
        assert any("Завтра" in btn for btn in buttons_text)
        assert "📅 Другая дата" in buttons_text
        assert "🔙 Главное меню" in buttons_text
    
    def test_get_date_keyboard_custom_days(self):
        """Тест клавиатуры выбора даты с кастомным количеством дней"""
        days = 14
        keyboard = KeyboardFactory.get_date_keyboard(days_ahead=days)
        
        # Считаем кнопки с датами (исключая доп. кнопки)
        date_buttons = [row for row in keyboard.inline_keyboard 
                       if any("📅" in btn.text for btn in row)]
        
        # Должно быть days + 2 кнопки (Другая дата, Главное меню)
        assert len(keyboard.inline_keyboard) >= days
    
    def test_get_date_keyboard_weekdays(self):
        """Тест правильности отображения дней недели"""
        keyboard = KeyboardFactory.get_date_keyboard(days_ahead=7)
        
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        
        # Проверяем что есть русские сокращения дней недели
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        found_weekdays = [wd for wd in weekdays if any(wd in btn for btn in buttons_text)]
        
        # Должен быть хотя бы один день недели
        assert len(found_weekdays) > 0
    
    def test_get_direction_keyboard(self):
        """Тест клавиатуры выбора направления"""
        keyboard = KeyboardFactory.get_direction_keyboard()
        
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        
        assert "🏙️ Минск → Островец" in buttons_text
        assert "🏘️ Островец → Минск" in buttons_text
        assert "🔄 Оба направления" not in buttons_text
        assert "🔙 Выбрать дату" in buttons_text
    
    def test_get_time_type_keyboard(self):
        """Тест клавиатуры выбора типа времени"""
        keyboard = KeyboardFactory.get_time_type_keyboard()
        
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        
        assert "🚀 Время отправления" in buttons_text
        assert "🎯 Время прибытия" in buttons_text
        assert "⏰ Любое время" in buttons_text
        assert "🔙 Выбрать направление" in buttons_text
    
    def test_get_time_range_keyboard(self):
        """Тест клавиатуры выбора временного диапазона"""
        keyboard = KeyboardFactory.get_time_range_keyboard()
        
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        
        # Проверяем наличие временных диапазонов
        assert any("Утром" in btn for btn in buttons_text)
        assert any("Днём" in btn for btn in buttons_text)
        assert any("Вечером" in btn for btn in buttons_text)
        assert any("Ночью" in btn for btn in buttons_text)
        assert "🕐 Пользовательский диапазон" in buttons_text
        assert "⏰ Любое время" in buttons_text
    
    def test_get_time_range_keyboard_departure(self):
        """Тест клавиатуры временного диапазона для отправления"""
        keyboard = KeyboardFactory.get_time_range_keyboard(time_type="departure")
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
    
    def test_get_time_range_keyboard_arrival(self):
        """Тест клавиатуры временного диапазона для прибытия"""
        keyboard = KeyboardFactory.get_time_range_keyboard(time_type="arrival")
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
    
    def test_callback_data_format(self):
        """Тест формата callback_data в кнопках"""
        keyboard = KeyboardFactory.get_direction_keyboard()
        
        # Проверяем что callback_data имеет правильный формат
        for row in keyboard.inline_keyboard:
            for btn in row:
                assert btn.callback_data is not None
                assert len(btn.callback_data) > 0


class TestKeyboardFactoryEdgeCases:
    """Тесты граничных случаев фабрики клавиатур"""
    
    def test_get_date_keyboard_zero_days(self):
        """Тест клавиатуры дат с нулевым количеством дней"""
        keyboard = KeyboardFactory.get_date_keyboard(days_ahead=0)
        
        # Должны быть хотя бы доп. кнопки
        assert len(keyboard.inline_keyboard) >= 2
    
    def test_get_date_keyboard_many_days(self):
        """Тест клавиатуры дат с большим количеством дней"""
        keyboard = KeyboardFactory.get_date_keyboard(days_ahead=30)
        
        # Должно создать клавиатуру без ошибок
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 30
    
    def test_date_formatting_today(self):
        """Тест форматирования даты для сегодня"""
        keyboard = KeyboardFactory.get_date_keyboard(days_ahead=1)
        
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        today_button = next(btn for btn in buttons_text if "Сегодня" in btn)
        
        # Должен содержать дату и день недели
        assert "(" in today_button
        assert ")" in today_button
    
    def test_date_formatting_tomorrow(self):
        """Тест форматирования даты для завтра"""
        keyboard = KeyboardFactory.get_date_keyboard(days_ahead=2)
        
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        tomorrow_button = next((btn for btn in buttons_text if "Завтра" in btn), None)
        
        assert tomorrow_button is not None
        assert "(" in tomorrow_button
        assert ")" in tomorrow_button
    
    def test_weekday_correctness(self):
        """Тест правильности дня недели"""
        keyboard = KeyboardFactory.get_date_keyboard(days_ahead=7)
        
        # Получаем кнопку сегодня
        today = datetime.now()
        expected_weekday = KeyboardFactory.WEEKDAYS[today.weekday()]
        
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        today_button = next(btn for btn in buttons_text if "Сегодня" in btn)
        
        # Проверяем что день недели правильный
        assert expected_weekday in today_button
    
    def test_all_buttons_have_text(self):
        """Тест что все кнопки имеют текст"""
        keyboards = [
            KeyboardFactory.get_main_menu_keyboard(12345, False),
            KeyboardFactory.get_date_keyboard(),
            KeyboardFactory.get_direction_keyboard(),
            KeyboardFactory.get_time_type_keyboard(),
            KeyboardFactory.get_time_range_keyboard()
        ]
        
        for keyboard in keyboards:
            for row in keyboard.inline_keyboard:
                for btn in row:
                    assert btn.text is not None
                    assert len(btn.text) > 0
                    assert btn.callback_data is not None
