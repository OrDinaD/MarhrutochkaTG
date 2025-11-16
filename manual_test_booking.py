"""
Ручной тест бронирования билета.
Запускается локально для проверки всего процесса.
"""

import asyncio
import sys
from src.utils.ticket_buyer import TicketBuyer

# Данные для теста
PHONE = "299605390"
PASSWORD = "Zxcvbnm,1"
FROM_CITY = "Островец"
TO_CITY = "Минск"
DATE = "2025-11-17"  # Завтра
PREFERRED_TIME = "11:30"  # Время с доступными местами


async def main():
    print("=" * 70)
    print("🧪 РУЧНОЙ ТЕСТ БРОНИРОВАНИЯ БИЛЕТА")
    print("=" * 70)
    print(f"📱 Телефон: +375{PHONE}")
    print(f"🚌 Маршрут: {FROM_CITY} → {TO_CITY}")
    print(f"📅 Дата: {DATE}")
    print(f"⏰ Предпочтительное время: {PREFERRED_TIME}")
    print("=" * 70)
    print()
    
    buyer = None
    
    try:
        # Шаг 1: Создание и запуск
        print("🔧 Шаг 1/4: Инициализация браузера...")
        buyer = TicketBuyer(
            phone=PHONE,
            password=PASSWORD,
            headless=False  # С видимым браузером для наблюдения
        )
        await buyer.start()
        print("✅ Браузер запущен\n")
        
        # Шаг 2: Вход
        print("🔐 Шаг 2/4: Вход в аккаунт...")
        login_success = await buyer.login()
        
        if not login_success:
            print("❌ Не удалось войти в аккаунт!")
            return False
        
        print("✅ Вход выполнен успешно\n")
        
        # Шаг 3: Поиск рейсов
        print(f"🔍 Шаг 3/4: Поиск рейсов {FROM_CITY} → {TO_CITY} на {DATE}...")
        routes = await buyer.search_tickets(
            from_city=FROM_CITY,
            to_city=TO_CITY,
            date=DATE
        )
        
        if not routes:
            print("❌ Рейсы не найдены!")
            print("   Возможные причины:")
            print("   - Нет рейсов на эту дату")
            print("   - Проблема с парсингом страницы")
            print("   - Изменилась структура сайта")
            return False
        
        print(f"✅ Найдено рейсов: {len(routes)}\n")
        
        # Показываем все рейсы
        print("📋 Список доступных рейсов:")
        print("-" * 70)
        for i, route in enumerate(routes[:10]):  # Показываем первые 10
            print(f"  {i+1}. {route.get('departure_time')} → {route.get('arrival_time')}")
            print(f"     Свободно: {route.get('available_seats')} мест | Цена: {route.get('price')} BYN")
            if route.get('company'):
                print(f"     Перевозчик: {route.get('company')}")
            print()
        
        if len(routes) > 10:
            print(f"  ... и еще {len(routes) - 10} рейсов")
            print()
        
        # Выбираем рейс
        target_route = None
        for route in routes:
            if route.get('departure_time') == PREFERRED_TIME:
                target_route = route
                break
        
        if not target_route:
            print(f"⚠️  Рейс с временем {PREFERRED_TIME} не найден")
            print(f"   Используем первый доступный рейс: {routes[0].get('departure_time')}")
            target_route = routes[0]
        else:
            print(f"🎯 Выбран рейс с временем {PREFERRED_TIME}")
        
        print()
        print("📌 Выбранный рейс:")
        print(f"   Отправление: {target_route.get('departure_time')}")
        print(f"   Прибытие: {target_route.get('arrival_time')}")
        print(f"   Свободно: {target_route.get('available_seats')} мест")
        print(f"   Цена: {target_route.get('price')} BYN")
        print()
        
        # Проверяем что есть свободные места
        if target_route.get('available_seats', 0) == 0:
            print("⚠️  На этом рейсе нет свободных мест!")
            print("   Бронирование невозможно")
            return False
        
        # Шаг 4: Бронирование
        print("🎫 Шаг 4/4: Бронирование билета...")
        print("   (Откроется страница выбора места)")
        print()
        
        booking_info = await buyer.book_ticket(route_info=target_route)
        
        # Сохраняем HTML для отладки
        print("💾 Сохранение HTML страницы бронирования...")
        html_content = await buyer.page.content()
        with open('debug_booking_page.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("   Сохранено: debug_booking_page.html")
        print()
        
        print("=" * 70)
        print("✅ БРОНИРОВАНИЕ ВЫПОЛНЕНО!")
        print("=" * 70)
        print()
        print("📋 Информация о бронировании:")
        for key, value in booking_info.items():
            print(f"   {key}: {value}")
        print()
        
        # Пауза для просмотра результата
        print("⏸️  Пауза 10 секунд для просмотра страницы...")
        await asyncio.sleep(10)
        
        print()
        print("=" * 70)
        print("✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        print("=" * 70)
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем (Ctrl+C)")
        return False
        
    except Exception as e:
        print(f"\n\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if buyer:
            print("\n🔒 Закрытие браузера...")
            await buyer.close()
            print("✅ Браузер закрыт")


if __name__ == "__main__":
    print()
    success = asyncio.run(main())
    print()
    
    sys.exit(0 if success else 1)
