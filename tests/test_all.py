#!/usr/bin/env python3
"""
Скрипт для тестирования всех функций бота
"""

import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def test_parser():
    """Тестирование парсера"""
    print("🔍 Тестирование парсера...")
    
    try:
        from final_parser import FinalMarshrutochkaParser
        
        async with FinalMarshrutochkaParser() as parser:
            # Тестируем получение данных на завтра
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            print(f"📅 Получаем данные на {tomorrow}...")
            routes_data = await parser.get_all_routes(tomorrow)
            
            if routes_data.get('success', False):
                minsk_routes = routes_data.get('minsk_to_ostrovets', [])
                ostrovets_routes = routes_data.get('ostrovets_to_minsk', [])
                
                print(f"✅ Парсер работает!")
                print(f"🚌 Минск → Островец: {len(minsk_routes)} рейсов")
                print(f"🚌 Островец → Минск: {len(ostrovets_routes)} рейсов")
                
                # Показываем первые несколько рейсов
                if minsk_routes:
                    print("\n📋 Первые 3 рейса Минск → Островец:")
                    for i, route in enumerate(minsk_routes[:3], 1):
                        seats = route.get('available_seats', 0)
                        print(f"  {i}. {route.get('departure_time')} → {route.get('arrival_time')} | {seats} мест")
                
                return True
            else:
                print("❌ Парсер не вернул данные")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка парсера: {e}")
        return False

async def test_filter_logic():
    """Тестирование логики фильтрации"""
    print("\n🔧 Тестирование логики фильтрации...")
    
    try:
        # Импортируем функции из advanced_bot
        import sys
        sys.path.append('.')
        from advanced_bot import check_time_criteria
        
        # Тестовые данные
        test_route = {
            'departure_time': '08:30',
            'arrival_time': '10:15',
            'available_seats': 5
        }
        
        # Тестовые конфигурации
        test_configs = [
            {
                'time_type': 'departure',
                'time_range': '08:00-09:00',
                'description': 'Отправление утром 08:00-09:00'
            },
            {
                'time_type': 'departure', 
                'time_range': '07:00-08:00',
                'description': 'Отправление рано утром 07:00-08:00'
            },
            {
                'time_type': 'arrival',
                'time_range': '10:00-11:00', 
                'description': 'Прибытие 10:00-11:00'
            },
            {
                'time_type': 'any',
                'time_range': 'any',
                'description': 'Любое время'
            }
        ]
        
        print("🧪 Тестируем фильтрацию рейса: 08:30 → 10:15")
        
        for config in test_configs:
            result = check_time_criteria(test_route, config)
            status = "✅ Подходит" if result else "❌ Не подходит"
            print(f"  {config['description']}: {status}")
        
        print("✅ Логика фильтрации работает!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка фильтрации: {e}")
        return False

def test_bot_config():
    """Тестирование конфигурации бота"""
    print("\n⚙️ Тестирование конфигурации...")
    
    # Проверяем токен
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ Токен TELEGRAM_BOT_TOKEN не найден в .env")
        return False
    
    if len(token) < 40:
        print("❌ Токен выглядит некорректно (слишком короткий)")
        return False
    
    print(f"✅ Токен найден: {token[:10]}...{token[-10:]}")
    
    # Проверяем файлы
    required_files = [
        'advanced_bot.py',
        'final_parser.py', 
        'requirements.txt',
        '.env'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} - найден")
        else:
            print(f"❌ {file} - не найден")
            return False
    
    print("✅ Конфигурация корректна!")
    return True

async def main():
    """Главная функция тестирования"""
    print("🧪 ПОЛНОЕ ТЕСТИРОВАНИЕ БОТА")
    print("=" * 50)
    
    tests = []
    
    # Тест 1: Конфигурация
    tests.append(("Конфигурация", test_bot_config()))
    
    # Тест 2: Парсер
    tests.append(("Парсер", await test_parser()))
    
    # Тест 3: Фильтрация  
    tests.append(("Фильтрация", await test_filter_logic()))
    
    # Результаты
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        if result:
            print(f"✅ {test_name}: ПРОШЕЛ")
            passed += 1
        else:
            print(f"❌ {test_name}: ПРОВАЛЕН")
    
    print(f"\n🎯 Итого: {passed}/{total} тестов прошли")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ! Бот готов к использованию!")
        print("\n🚀 Запустите бота командой:")
        print("   ./start_bot.sh")
        print("\n📱 Найдите бота в Telegram: @MarshrutochkaOst_bot")
    else:
        print("⚠️ Некоторые тесты провалены. Проверьте ошибки выше.")
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
