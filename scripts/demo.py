#!/usr/bin/env python3
"""
Демонстрационный скрипт для тестирования новых функций аутентификации
"""

import asyncio
import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_auth_manager():
    """Тестирование менеджера аутентификации"""
    print("🧪 Тестирование системы аутентификации...")
    print("=" * 60)
    
    try:
        from auth_manager import AuthManager
        from ticket_formatter import TicketFormatter
        
        # Инициализируем менеджер аутентификации
        async with AuthManager() as auth:
            print("✅ AuthManager инициализирован")
            
            # Тестовые данные
            user_id = 12345  # Тестовый ID пользователя
            phone = "+375299605390"
            password = "Zxcvbnm,1"
            
            print(f"\n🔐 Попытка авторизации с номером {phone}...")
            
            # Попытка входа
            success = await auth.login(user_id, phone, password)
            
            if success:
                print("✅ Авторизация успешна!")
                
                # Получаем информацию профиля
                print("\n👤 Получение информации профиля...")
                profile_info = await auth.get_profile_info(user_id)
                
                formatted_profile = TicketFormatter.format_profile_info(profile_info)
                print("\n📋 Информация профиля:")
                print(formatted_profile)
                
                # Получаем список бронирований
                print("\n🎫 Получение списка бронирований...")
                bookings = await auth.get_bookings(user_id)
                
                formatted_bookings = TicketFormatter.format_booking_list(bookings)
                print("\n📋 Список бронирований:")
                print(formatted_bookings)
                
                # Тестируем поиск маршрутов
                print("\n🔍 Тестирование поиска маршрутов...")
                routes = await auth.search_routes(user_id, from_city="Минск", to_city="Островец", date="2025-07-10")
                
                formatted_routes = TicketFormatter.format_route_search_results(routes)
                print("\n🚌 Результаты поиска:")
                print(formatted_routes)
                
                # Тестируем проверку статуса бронирования
                print("\n📋 Тестирование проверки статуса бронирования...")
                status = await auth.check_booking_status(user_id, "TEST12345", "5390")
                
                formatted_status = TicketFormatter.format_booking_status(status)
                print("\n📊 Статус бронирования:")
                print(formatted_status)
                
            else:
                print("❌ Авторизация не удалась")
                print("💡 Возможные причины:")
                print("   • Неверные учетные данные")
                print("   • Проблемы с сетью")
                print("   • Временные проблемы сайта")
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Убедитесь, что все модули находятся в папке src/")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def test_ticket_formatter():
    """Тестирование форматтера билетов"""
    print("🎨 Тестирование форматтера билетов...")
    print("=" * 60)
    
    try:
        from ticket_formatter import TicketFormatter
        
        # Тестовые данные билета
        test_ticket = {
            'route': 'Минск → Островец',
            'date': '10.07.2025',
            'time': '08:30',
            'trip_number': 'M101',
            'seat': '15A',
            'price': '12.50 BYN',
            'departure': 'Минск, Автовокзал Восточный',
            'arrival': 'Островец, Автостанция',
            'status': 'confirmed',
            'booking_number': 'MB2025071001',
            'contact': '+375293541000'
        }
        
        print("🎫 Пример билета:")
        formatted_ticket = TicketFormatter.format_ticket(test_ticket)
        print(formatted_ticket)
        
        # Тестовые данные профиля
        test_profile = {
            'name': 'Иван Иванов',
            'phone': '+375299605390',
            'email': 'ivan@example.com',
            'balance': '25.00 BYN',
            'url': 'https://билет.маршруточка.бел/profile',
            'timestamp': '2025-07-04T12:00:00'
        }
        
        print("\n👤 Пример профиля:")
        formatted_profile = TicketFormatter.format_profile_info(test_profile)
        print(formatted_profile)
        
        # Тестовые данные бронирований
        test_bookings = [
            {
                'route': 'Минск → Островец',
                'date': '10.07.2025',
                'time': '08:30',
                'price': '12.50 BYN',
                'status': 'confirmed',
                'booking_number': 'MB2025071001'
            },
            {
                'route': 'Островец → Минск',
                'date': '12.07.2025',
                'time': '17:45',
                'price': '12.50 BYN',
                'status': 'pending',
                'booking_number': 'MB2025071002'
            }
        ]
        
        print("\n📋 Пример списка бронирований:")
        formatted_bookings = TicketFormatter.format_booking_list(test_bookings)
        print(formatted_bookings)
        
        # Тестовые данные маршрутов
        test_routes = [
            {
                'route': 'Минск → Островец',
                'departure_time': '08:30',
                'arrival_time': '10:15',
                'duration': '1ч 45м',
                'price': '12.50 BYN',
                'available_seats': '8',
                'vehicle_type': 'Mercedes Sprinter',
                'carrier': 'ИП Петров А.А.',
                'stops': ['Молодечно', 'Сморгонь']
            },
            {
                'route': 'Минск → Островец',
                'departure_time': '14:20',
                'arrival_time': '16:05',
                'duration': '1ч 45м',
                'price': '12.50 BYN',
                'available_seats': '12',
                'vehicle_type': 'Iveco Daily'
            }
        ]
        
        print("\n🚌 Пример результатов поиска:")
        formatted_routes = TicketFormatter.format_route_search_results(test_routes)
        print(formatted_routes)
        
        print("\n✅ Все тесты форматтера выполнены успешно!")
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def main():
    """Главная функция демо"""
    print("🚀 Демонстрация новых функций MarhrutochkaTG")
    print("=" * 60)
    
    # Тестируем форматтер (не требует интернет)
    await test_ticket_formatter()
    
    # Спрашиваем пользователя о тестировании аутентификации
    print("\n" + "=" * 60)
    test_auth = input("🤔 Хотите протестировать систему аутентификации? (y/N): ").lower()
    
    if test_auth in ['y', 'yes', 'да']:
        print("\n⚠️  ВНИМАНИЕ: Для тестирования будут использованы реальные учетные данные")
        print("📱 Номер: +375299605390")
        print("🔑 Пароль: Zxcvbnm,1")
        print("\n🌐 Будет выполнено подключение к сайту билет.маршруточка.бел")
        
        confirm = input("\n✅ Продолжить? (y/N): ").lower()
        if confirm in ['y', 'yes', 'да']:
            await test_auth_manager()
        else:
            print("⏹️  Тестирование аутентификации отменено")
    
    print("\n" + "=" * 60)
    print("🎉 Демонстрация завершена!")
    print("\n💡 Следующие шаги:")
    print("   1. Установите Playwright браузеры: playwright install chromium")
    print("   2. Настройте .env файл с токеном бота")
    print("   3. Запустите бота: python main.py")
    print("   4. Протестируйте новые команды: /login, /profile, /bookings")

if __name__ == "__main__":
    asyncio.run(main())
