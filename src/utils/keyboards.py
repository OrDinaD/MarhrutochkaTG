#!/usr/bin/env python3
"""
Модуль для создания клавиатур Telegram бота
Вынесен из основного файла для лучшей организации кода
"""
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from typing import List, Optional, Dict


class KeyboardFactory:
    """Фабрика для создания клавиатур"""
    
    # Русские сокращения дней недели
    WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    @staticmethod
    def get_main_menu_keyboard(user_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
        """Создает клавиатуру главного меню"""
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск рейсов", callback_data="search_routes")],
            [InlineKeyboardButton("🔔 Настроить мониторинг", callback_data="setup_monitoring")],
            [InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors")],
            [InlineKeyboardButton("🤖 Автопокупка билетов", callback_data="autobuy_menu")],
            [InlineKeyboardButton("🔐 Управление аккаунтом", callback_data="account_menu")],
            [InlineKeyboardButton("🌐 Открыть сайт", callback_data="open_website")]
        ]

        # Добавляем админ-панель для администратора
        if is_admin:
            keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")])

        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_date_keyboard(days_ahead: int = 7) -> InlineKeyboardMarkup:
        """Создает клавиатуру для выбора даты"""
        today = datetime.now()
        dates = []
        
        for i in range(days_ahead):
            date = today + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            # Форматируем дату как dd.mm + день недели
            day_name = f"{date.strftime('%d.%m')} {KeyboardFactory.WEEKDAYS[date.weekday()]}"
            
            if i == 0:
                label = f"📅 Сегодня ({day_name})"
            elif i == 1:
                label = f"📅 Завтра ({day_name})"
            else:
                label = f"📅 {day_name}"
            
            dates.append([InlineKeyboardButton(label, callback_data=f"date_{date_str}")])
        
        dates.extend([
            [InlineKeyboardButton("📅 Другая дата", callback_data="custom_date")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ])
        
        return InlineKeyboardMarkup(dates)
    
    @staticmethod
    def get_direction_keyboard(include_all: bool = False) -> InlineKeyboardMarkup:
        """Создает клавиатуру для выбора направления"""
        keyboard = [
            [InlineKeyboardButton("🏙️ Минск → Островец", callback_data="dir_minsk_ostrovets")],
            [InlineKeyboardButton("🏘️ Островец → Минск", callback_data="dir_ostrovets_minsk")]
        ]
        
        if include_all:
            keyboard.append([InlineKeyboardButton("🔄 Оба направления", callback_data="dir_both")])
            
        keyboard.append([InlineKeyboardButton("🔙 Выбрать дату", callback_data="back_to_date")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_time_type_keyboard() -> InlineKeyboardMarkup:
        """Создает клавиатуру для выбора типа времени"""
        keyboard = [
            [InlineKeyboardButton("🚀 Время отправления", callback_data="time_departure")],
            [InlineKeyboardButton("🎯 Время прибытия", callback_data="time_arrival")],
            [InlineKeyboardButton("⏰ Любое время", callback_data="time_any")],
            [InlineKeyboardButton("🔙 Выбрать направление", callback_data="back_to_direction")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_time_range_keyboard(time_type: str = "departure") -> InlineKeyboardMarkup:
        """Создает клавиатуру для выбора диапазона времени"""
        ranges = [
            ("🌅 Утром (05:00-09:00)", "05:00-09:00"),
            ("☀️ Днём (09:00-15:00)", "09:00-15:00"),
            ("🌆 Вечером (15:00-20:00)", "15:00-20:00"),
            ("🌙 Ночью (20:00-05:00)", "20:00-05:00"),
            ("🕐 Пользовательский диапазон", "custom"),
            ("⏰ Любое время", "any")
        ]
        
        keyboard = []
        for label, value in ranges:
            keyboard.append([InlineKeyboardButton(label, callback_data=f"range_{value}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Тип времени", callback_data="back_to_time_type")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_webapp_keyboard(
        direction: Optional[str] = None, 
        date: Optional[str] = None,
        additional_buttons: Optional[List[List[InlineKeyboardButton]]] = None
    ) -> InlineKeyboardMarkup:
        """Создает клавиатуру с кнопками веб-приложений"""
        keyboard = []
        
        # Создаем кнопку для доступа к сайту маршруточки
        base_url = "https://билет.маршруточка.бел/"
        keyboard.append([
            InlineKeyboardButton(
                "🚌 Открыть сайт маршруточки", 
                web_app=WebAppInfo(url=base_url)
            )
        ])
        
        # Добавляем дополнительные кнопки если есть
        if additional_buttons:
            keyboard.extend(additional_buttons)
        
        return InlineKeyboardMarkup(keyboard)
    
# Создаем глобальный экземпляр для использования в боте
keyboard_factory = KeyboardFactory()
