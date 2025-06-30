#!/usr/bin/env python3
"""
Демонстрация возможностей Telegram-бота маршруточки
"""

import asyncio
from datetime import datetime, timedelta
from final_parser import FinalMarshrutochkaParser

def format_route(route, index=None):
    """Форматирование маршрута для демонстрации"""
    prefix = f"{index}. " if index else ""
    
    departure = route.get('departure_time', 'н/д')
    arrival = route.get('arrival_time', 'н/д')
    duration = route.get('duration', 'н/д')
    seats = route.get('available_seats', 'н/д')
    carrier = route.get('carrier', 'н/д')
    
    # Эмодзи для количества мест
    if isinstance(seats, int):
        if seats == 0:
            seats_emoji = "🚫"
        elif seats <= 3:
            seats_emoji = "🔥"
        elif seats <= 5:
            seats_emoji = "⚠️"
        else:
            seats_emoji = "✅"
    else:
        seats_emoji = "❓"
    
    return f"{prefix}{departure} → {arrival} ({duration}) | {seats_emoji} {seats} мест | 🏢{carrier}"

async def demo_search_routes():
    """Демонстрация поиска рейсов"""
    print("🔍 ДЕМОНСТРАЦИЯ ПОИСКА РЕЙСОВ")
    print("=" * 60)
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    async with FinalMarshrutochkaParser() as parser:
        print(f"📅 Поиск рейсов на {tomorrow}")
        print("⏳ Выполняется запрос к сайту...")
        
        routes_data = await parser.get_all_routes(tomorrow)
        
        if routes_data.get('success', False):
            minsk_routes = routes_data.get('minsk_to_ostrovets', [])
            ostrovets_routes = routes_data.get('ostrovets_to_minsk', [])
            
            print(f"✅ Данные получены успешно!")
            print(f"🕐 Время парсинга: {routes_data.get('search_time', 'н/д')}")
            print()
            
            # Показываем первые 5 рейсов каждого направления
            print("🚌 МИНСК → ОСТРОВЕЦ")
            print("-" * 40)
            if minsk_routes:
                for i, route in enumerate(minsk_routes[:5], 1):
                    print(format_route(route, i))
                if len(minsk_routes) > 5:
                    print(f"... и еще {len(minsk_routes) - 5} рейсов")
            else:
                print("❌ Рейсы не найдены")
            
            print()
            print("🚌 ОСТРОВЕЦ → МИНСК") 
            print("-" * 40)
            if ostrovets_routes:
                for i, route in enumerate(ostrovets_routes[:5], 1):
                    print(format_route(route, i))
                if len(ostrovets_routes) > 5:
                    print(f"... и еще {len(ostrovets_routes) - 5} рейсов")
            else:
                print("❌ Рейсы не найдены")
            
            print()
            print("📊 СТАТИСТИКА")
            print("-" * 40)
            total_routes = len(minsk_routes) + len(ostrovets_routes)
            print(f"📈 Всего найдено рейсов: {total_routes}")
            
            # Статистика по местам
            no_seats = sum(1 for r in minsk_routes + ostrovets_routes 
                          if r.get('available_seats') == 0)
            few_seats = sum(1 for r in minsk_routes + ostrovets_routes 
                           if isinstance(r.get('available_seats'), int) and 
                           1 <= r.get('available_seats') <= 3)
            many_seats = sum(1 for r in minsk_routes + ostrovets_routes 
                            if isinstance(r.get('available_seats'), int) and 
                            r.get('available_seats') > 5)
            
            print(f"🚫 Без мест: {no_seats}")
            print(f"🔥 Мало мест (1-3): {few_seats}")
            print(f"✅ Много мест (6+): {many_seats}")
            
        else:
            print("❌ Не удалось получить данные о рейсах")

def demo_bot_commands():
    """Демонстрация команд бота"""
    print("\n\n🤖 ДЕМОНСТРАЦИЯ КОМАНД TELEGRAM-БОТА")
    print("=" * 60)
    
    commands = [
        ("/start", "Запуск бота и приветствие", "Показывает приветствие и список команд"),
        ("/help", "Справка по командам", "Подробная информация о всех возможностях бота"),
        ("/search 2025-01-15", "Поиск рейсов на дату", "Найти все рейсы на указанную дату"),
        ("/today", "Рейсы на сегодня", "Показать рейсы на текущий день"),
        ("/tomorrow", "Рейсы на завтра", "Показать рейсы на завтрашний день"),
        ("/subscribe 2025-01-15", "Подписка на уведомления", "Получать уведомления о рейсах на дату"),
        ("/unsubscribe", "Отписка от уведомлений", "Перестать получать уведомления")
    ]
    
    for cmd, desc, details in commands:
        print(f"🔹 {cmd}")
        print(f"   📝 {desc}")
        print(f"   💡 {details}")
        print()

def demo_monitoring_features():
    """Демонстрация возможностей мониторинга"""
    print("🔔 ВОЗМОЖНОСТИ МОНИТОРИНГА")
    print("=" * 60)
    
    features = [
        ("Автоматический мониторинг", "Проверка рейсов каждые 30 минут (настраивается)"),
        ("Умные уведомления", "Уведомления только при наличии свободных мест"),
        ("Пороговые значения", "Уведомления при количестве мест ≥ 5 (настраивается)"),
        ("Группировка подписок", "Оптимизация запросов для нескольких пользователей"),
        ("Персональные подписки", "Каждый пользователь может подписаться на свою дату"),
        ("Логирование", "Полная история работы бота сохраняется в файлы"),
        ("Обработка ошибок", "Graceful обработка сбоев сайта и сети")
    ]
    
    for title, description in features:
        print(f"✨ {title}")
        print(f"   {description}")
        print()

def demo_technical_info():
    """Техническая информация"""
    print("⚙️ ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ")
    print("=" * 60)
    
    tech_info = [
        ("Язык программирования", "Python 3.13+"),
        ("Telegram API", "python-telegram-bot 22.2"),
        ("HTTP клиент", "aiohttp для асинхронных запросов"),
        ("HTML парсинг", "BeautifulSoup4 для извлечения данных"),
        ("Планировщик задач", "APScheduler для периодического мониторинга"),
        ("Конфигурация", "python-dotenv для управления настройками"),
        ("Асинхронность", "Полная поддержка async/await"),
        ("Логирование", "Встроенный модуль logging с ротацией файлов")
    ]
    
    for component, description in tech_info:
        print(f"🔧 {component}: {description}")
    
    print()
    print("📁 СТРУКТУРА ФАЙЛОВ:")
    files = [
        ("telegram_bot.py", "Основной код Telegram-бота"),
        ("final_parser.py", "Парсер сайта маршруточки"),
        ("run_bot.py", "Launcher с логированием"),
        ("bot_utils.py", "Утилиты для тестирования"),
        ("test_bot.py", "Тестирование подключения к Telegram"),
        (".env", "Конфигурационные переменные"),
        ("logs/", "Директория с логами работы бота")
    ]
    
    for filename, description in files:
        print(f"📄 {filename} - {description}")

async def main():
    """Главная демонстрационная функция"""
    print("🚌 ДЕМОНСТРАЦИЯ TELEGRAM-БОТА МОНИТОРИНГА МАРШРУТОЧКИ")
    print("🌐 Сайт: https://билет.маршруточка.бел")
    print("🛣️  Направления: Минск ⇄ Островец")
    print("=" * 80)
    
    # Демонстрация поиска рейсов
    await demo_search_routes()
    
    # Демонстрация команд бота
    demo_bot_commands()
    
    # Демонстрация мониторинга
    demo_monitoring_features()
    
    # Техническая информация
    demo_technical_info()
    
    print("\n" + "=" * 80)
    print("🎯 ГОТОВО К ИСПОЛЬЗОВАНИЮ!")
    print("🚀 Для запуска бота выполните: python run_bot.py")
    print("🧪 Для тестирования выполните: python test_bot.py")
    print("💡 Для получения справки выполните: python bot_utils.py --help")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
