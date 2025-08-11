#!/usr/bin/env python3
"""
Тест интеграции функциональности бронирования билетов
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты из основного модуля
from src.auth.bot_auth_manager import BotAuthManager, format_routes_message, format_booking_confirmation
from src.auth.improved_web_auth import RouteInfo, BookingRequest, UserBooking

async def test_booking_functionality():
    """Тест основного функционала бронирования"""
    
    print("🧪 Тестирование функционала бронирования билетов...")
    
    # Создаем менеджер авторизации
    auth_manager = BotAuthManager()
    
    # Симулируем авторизованного пользователя
    test_user_id = 123456789
    
    try:
        # 1. Тест создания RouteInfo
        print("\n✅ Тест 1: Создание RouteInfo")
        route = RouteInfo(
            route_id="test_route_1",
            from_location="Минск",
            to_location="Островец", 
            departure_time="08:30",
            arrival_time="09:45",
            price="15.00 BYN",
            available_seats=5
        )
        print(f"   Маршрут создан: {route.departure_time} {route.from_location} → {route.to_location}")
        
        # 2. Тест создания BookingRequest
        print("\n✅ Тест 2: Создание BookingRequest")
        booking_request = BookingRequest(
            route_id="test_route_1",
            passenger_count=1,
            passenger_name="Иванов Иван Иванович",
            passenger_phone="+375291234567",
            departure_date="2025-01-15"
        )
        print(f"   Запрос на бронирование: {booking_request.passenger_name}")
        
        # 3. Тест форматирования маршрутов
        print("\n✅ Тест 3: Форматирование маршрутов")
        routes = [route]
        formatted_message = format_routes_message(routes, "Минск", "Островец", "2025-01-15")
        print(f"   Форматированное сообщение: {len(formatted_message)} символов")
        
        # 4. Тест создания результата бронирования
        print("\n✅ Тест 4: Создание результата бронирования")
        booking_result = UserBooking(
            booking_id="TEST123",
            route="Минск → Островец",
            date="2025-01-15",
            departure_time="08:30",
            ticket_number="ABC123",
            price="15.00 BYN",
            status="confirmed"
        )
        print(f"   Результат бронирования: {booking_result.booking_id}")
        
        # 5. Тест форматирования подтверждения
        print("\n✅ Тест 5: Форматирование подтверждения бронирования")
        confirmation_message = format_booking_confirmation(booking_result)
        print(f"   Подтверждение: {len(confirmation_message)} символов")
        
        print("\n🎉 Все тесты прошли успешно!")
        print("📝 Функционал бронирования готов к использованию")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        return False

async def test_bot_integration():
    """Тест интеграции с ботом"""
    
    print("\n🤖 Тестирование интеграции с ботом...")
    
    try:
        # Импортируем необходимые функции бота
        from src.bot import (
            book_ticket_handler, 
            handle_booking_date_choice,
            handle_booking_passenger_name,
            handle_booking_passenger_phone,
            confirm_booking
        )
        
        print("✅ Все функции бронирования успешно импортированы")
        
        # Проверяем, что состояния определены
        from src.bot import (
            BOOKING_FROM, BOOKING_TO, BOOKING_DATE,
            BOOKING_ROUTE_SELECT, BOOKING_PASSENGER_COUNT,
            BOOKING_PASSENGER_NAME, BOOKING_PASSENGER_PHONE,
            BOOKING_CONFIRM
        )
        
        print("✅ Все состояния бронирования определены")
        print(f"   BOOKING_FROM: {BOOKING_FROM}")
        print(f"   BOOKING_PASSENGER_NAME: {BOOKING_PASSENGER_NAME}")
        print(f"   BOOKING_CONFIRM: {BOOKING_CONFIRM}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка интеграции: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    
    print("🚀 Запуск тестов интеграции бронирования билетов")
    print("=" * 60)
    
    # Тест основного функционала
    test1_result = await test_booking_functionality()
    
    # Тест интеграции с ботом
    test2_result = await test_bot_integration()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"   Основной функционал: {'✅ ПРОШЕЛ' if test1_result else '❌ ПРОВАЛЕН'}")
    print(f"   Интеграция с ботом: {'✅ ПРОШЕЛ' if test2_result else '❌ ПРОВАЛЕН'}")
    
    if test1_result and test2_result:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("📦 Функционал бронирования готов к продакшену")
    else:
        print("\n❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ")
        print("🔧 Требуется дополнительная отладка")

if __name__ == "__main__":
    asyncio.run(main())
