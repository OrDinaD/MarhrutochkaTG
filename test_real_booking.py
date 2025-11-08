#!/usr/bin/env python3
"""
Интеграционный тест реальной покупки билета
Островец → Минск, 2025-11-09, 07:00
"""
import asyncio
import sys
import os
from datetime import datetime

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.ticket_buyer import TicketBuyer
from managers.account_manager import AccountManager


async def test_real_booking():
    """Тест реального поиска и бронирования билета"""
    
    print("=" * 60)
    print("🧪 ИНТЕГРАЦИОННЫЙ ТЕСТ ПОКУПКИ БИЛЕТА")
    print("=" * 60)
    
    # Данные для теста
    phone = "299605390"
    password = "Zxcvbnm,1"
    from_city = "Островец"
    to_city = "Минск"
    date = "2025-11-09"
    preferred_time = "07:00"
    
    print(f"\n📋 Параметры теста:")
    print(f"   Телефон: +375{phone}")
    print(f"   Маршрут: {from_city} → {to_city}")
    print(f"   Дата: {date}")
    print(f"   Время: {preferred_time}")
    print()
    
    try:
        # Создаем покупателя билетов (НЕ headless для отладки)
        print("🔧 Создание покупателя билетов (с видимым браузером)...")
        async with TicketBuyer(
            phone=phone,
            password=password,
            headless=False  # Видимый браузер для отладки
        ) as buyer:
            print("✅ Покупатель создан\n")
            
            # Шаг 1: Вход в аккаунт
            print("🔐 Шаг 1: Вход в аккаунт...")
            await buyer.login()
            print("✅ Вход выполнен успешно\n")
            
            # Шаг 2: Поиск билетов
            print(f"🔍 Шаг 2: Поиск билетов {from_city} → {to_city} на {date}...")
            routes = await buyer.search_tickets(
                from_city=from_city,
                to_city=to_city,
                date=date,
                seats=1
            )
            
            print(f"📊 Найдено рейсов: {len(routes)}\n")
            
            if not routes:
                print("❌ ПРОБЛЕМА: Рейсы не найдены!")
                print("\n🔍 Делаем скриншот страницы результатов...")
                await buyer.page.screenshot(path="debug_search_results.png")
                print("💾 Скриншот сохранен: debug_search_results.png")
                
                print("\n📄 Получаем HTML страницы...")
                html = await buyer.page.content()
                with open("debug_search_results.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("💾 HTML сохранен: debug_search_results.html")
                
                return False
            
            # Выводим все найденные рейсы
            print("📋 Список найденных рейсов:")
            print("-" * 60)
            for i, route in enumerate(routes):
                print(f"Рейс {i}:")
                print(f"  Отправление: {route.get('departure_time', 'N/A')}")
                print(f"  Прибытие: {route.get('arrival_time', 'N/A')}")
                print(f"  Свободно мест: {route.get('available_seats', 'N/A')}")
                print(f"  Цена: {route.get('price', 'N/A')} BYN")
                print(f"  Индекс: {route.get('index', 'N/A')}")
                print()
            
            # Фильтруем по времени 07:00
            print(f"🎯 Поиск рейса с временем отправления {preferred_time}...")
            target_route = None
            for route in routes:
                if route.get('departure_time') == preferred_time:
                    target_route = route
                    break
            
            if not target_route:
                print(f"⚠️  Рейс с временем {preferred_time} не найден")
                print(f"   Используем первый доступный рейс...")
                target_route = routes[0]
            
            print(f"✅ Выбран рейс:")
            print(f"   Отправление: {target_route.get('departure_time')}")
            print(f"   Прибытие: {target_route.get('arrival_time')}")
            print(f"   Свободно: {target_route.get('available_seats')} мест")
            print(f"   Цена: {target_route.get('price')} BYN\n")
            
            # Шаг 3: Бронирование билета
            print(f"🎫 Шаг 3: Бронирование билета...")
            
            booking_info = await buyer.book_ticket(route_info=target_route)
            
            print("✅ Бронирование выполнено!")
            print(f"📋 Информация о бронировании:")
            for key, value in booking_info.items():
                print(f"   {key}: {value}")
            
            print("\n" + "=" * 60)
            print("✅ ТЕСТ УСПЕШНО ЗАВЕРШЕН!")
            print("=" * 60)
            
            # Делаем паузу чтобы увидеть результат
            print("\n⏸️  Пауза 5 секунд для просмотра результата...")
            await asyncio.sleep(5)
            
            return True
            
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Запуск теста реального бронирования...")
    print("⚠️  ВНИМАНИЕ: Тест использует РЕАЛЬНЫЕ данные аккаунта!")
    print("⚠️  Будет выполнено РЕАЛЬНОЕ бронирование билета!\n")
    
    # Запускаем тест
    success = asyncio.run(test_real_booking())
    
    if success:
        print("\n✅ Все этапы выполнены успешно!")
        sys.exit(0)
    else:
        print("\n❌ Тест завершился с ошибкой")
        sys.exit(1)
