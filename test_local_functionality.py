#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки локальной функциональности бота
"""

import os
import sys
import json
import logging
import asyncio
from dotenv import load_dotenv
from src.parser import FinalMarshrutochkaParser
from src.bot import get_main_menu_keyboard

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_parsers():
    """Тест функциональности парсера"""
    logger.info("🧪 Тестирование парсера маршрутов")
    
    async with FinalMarshrutochkaParser() as parser:
        # Тестовые города и даты (только поддерживаемые города из city_mapping)
        test_cases = [
            {"from_city": "Минск", "to_city": "Островец", "date": "2025-07-15"},
            {"from_city": "Островец", "to_city": "Минск", "date": "2025-07-20"}
        ]
        
        for tc in test_cases:
            logger.info(f"Поиск маршрута: {tc['from_city']} → {tc['to_city']} на {tc['date']}")
                
            # Поиск маршрутов через метод search_routes
            routes = await parser.search_routes(tc["from_city"], tc["to_city"], tc["date"])
            
            if routes:
                logger.info(f"✅ Найдено {len(routes)} маршрутов")
                # Выводим первые 2 маршрута для проверки
                for i, route in enumerate(routes[:2]):
                    logger.info(f"  {i+1}. {route['departure_time']} → {route['arrival_time']}, "
                               f"Свободно мест: {route['free_seats']}, Цена: {route['price']}")
            else:
                logger.warning(f"⚠️ Маршруты не найдены")

def test_keyboards():
    """Тест генерации клавиатур"""
    logger.info("🧪 Тестирование генерации клавиатур")
    
    # Тест основной клавиатуры для разных пользователей
    test_user_id = 123456789  # Тестовый ID пользователя
    keyboard = get_main_menu_keyboard(test_user_id)
    logger.info(f"Главная клавиатура для пользователя {test_user_id}: {keyboard}")
    
    # Еще один тестовый ID
    test_user_id2 = 987654321
    keyboard2 = get_main_menu_keyboard(test_user_id2)
    logger.info(f"Главная клавиатура для пользователя {test_user_id2}: {keyboard2}")

def test_session_persistence():
    """Тест сохранения и загрузки сессий"""
    logger.info("🧪 Тестирование сохранения/загрузки сессий и мониторингов")
    
    # Проверяем наличие файла мониторингов
    if os.path.exists("monitors.json"):
        with open("monitors.json", "r", encoding="utf-8") as f:
            monitors_data = json.load(f)
            logger.info(f"📊 Найдены мониторинги для {len(monitors_data)} пользователей: {list(monitors_data.keys())}")
    else:
        logger.warning("⚠️ Файл monitors.json не найден")
    
    # Проверяем наличие файла сессий пользователей
    if os.path.exists("user_sessions.json"):
        with open("user_sessions.json", "r", encoding="utf-8") as f:
            sessions_data = json.load(f)
            logger.info(f"🔓 Найдены сессии для {len(sessions_data)} пользователей: {list(sessions_data.keys())}")
    else:
        logger.warning("⚠️ Файл user_sessions.json не найден")

async def main():
    """Основная функция тестирования"""
    logger.info("🚀 Начало тестирования локальной функциональности бота")
    
    # Загрузка переменных окружения
    load_dotenv()
    
    # Проверка наличия токена
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        return
    else:
        logger.info(f"✅ TELEGRAM_BOT_TOKEN найден, первые 5 символов: {token[:5]}...")
    
    # Тестирование парсера
    await test_parsers()
    
    # Тестирование клавиатур
    test_keyboards()
    
    # Тестирование сохранения/загрузки сессий
    test_session_persistence()
    
    logger.info("🏁 Тестирование завершено")

if __name__ == "__main__":
    asyncio.run(main())
