#!/usr/bin/env python3
"""
Тестирование с реальными данными для сайта маршрутки
"""

import os
import sys
import json
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from requests_auth import RequestsAuthManager


def test_real_auth():
    """Тест с реальными данными"""
    print("=== Тестирование с реальными данными ===")
    print("🌐 Сайт: https://xn--90aiim0b.xn--80aa3agllaqi6bg.xn--90ais/ (билет.маршруточка.бел)")
    print()
    
    # Используем данные из вашего сообщения
    username = "+375299605390"
    password = "Zxcvbnm,1"
    
    print("⚠️  Используются реальные данные для входа")
    print(f"📱 Телефон: {username}")
    print(f"🔑 Пароль: {password[:3]}{'*' * (len(password) - 3)}")
    print()
    
    # Создаем менеджер аутентификации
    with RequestsAuthManager() as auth_manager:
        print("1. Создан RequestsAuthManager")
        
        # Проверяем доступность сайта
        print("\n2. Проверка доступности сайта...")
        try:
            response = auth_manager.session.get(auth_manager.base_url, timeout=10)
            print(f"✅ Сайт доступен, статус: {response.status_code}")
            print(f"📊 Итоговый URL: {response.url}")
            print(f"🍪 Cookies: {dict(auth_manager.session.cookies)}")
        except Exception as e:
            print(f"❌ Сайт недоступен: {e}")
            return False
        
        # Тест получения страницы входа
        print("\n3. Тестирование получения страницы входа...")
        success, csrf_token = auth_manager.get_login_page()
        if success:
            print(f"✅ Страница входа получена")
            if csrf_token:
                print(f"🔐 CSRF токен: {csrf_token[:10]}...")
            else:
                print("⚠️  CSRF токен не найден")
            print(f"🍪 Cookies: {dict(auth_manager.session.cookies)}")
        else:
            print("❌ Не удалось получить страницу входа")
            return False
        
        # Тест входа
        print(f"\n4. Тестирование входа...")
        login_success = auth_manager.login(username, password)
        
        if login_success:
            print("✅ Вход выполнен успешно!")
            print(f"🍪 Cookies после входа: {dict(auth_manager.session.cookies)}")
            
            # Тест получения профиля
            print("\n5. Тестирование получения профиля...")
            profile_result = auth_manager.get_profile_info()
            
            if profile_result['success']:
                print("✅ Профиль получен!")
                print(f"🔗 URL профиля: {profile_result.get('url', 'не указан')}")
                print("📋 Данные профиля:")
                print(json.dumps(profile_result['data'], indent=2, ensure_ascii=False))
            else:
                print(f"❌ Не удалось получить профиль: {profile_result.get('error', 'неизвестная ошибка')}")
                
                # Попробуем прямой переход на страницу профиля
                print("\n   Попытка прямого перехода на /profile...")
                try:
                    profile_response = auth_manager.session.get(f"{auth_manager.base_url}/profile", timeout=10)
                    print(f"   Статус: {profile_response.status_code}")
                    print(f"   URL: {profile_response.url}")
                    if profile_response.status_code == 200:
                        print("   ✅ Доступ к профилю есть!")
                    else:
                        print(f"   ❌ Доступ к профилю ограничен: {profile_response.status_code}")
                except Exception as e:
                    print(f"   ❌ Ошибка при доступе к профилю: {e}")
            
            # Тест получения бронирований
            print("\n6. Тестирование получения бронирований...")
            bookings_result = auth_manager.get_bookings()
            
            if bookings_result['success']:
                print("✅ Бронирования получены!")
                print(f"🔗 URL бронирований: {bookings_result.get('url', 'не указан')}")
                print(f"📋 Количество бронирований: {len(bookings_result['bookings'])}")
                
                for i, booking in enumerate(bookings_result['bookings'], 1):
                    print(f"\n   🎫 Бронирование {i}:")
                    print(json.dumps(booking, indent=4, ensure_ascii=False))
                    
            else:
                print(f"❌ Не удалось получить бронирования: {bookings_result.get('error', 'неизвестная ошибка')}")
            
            # Попробуем исследовать структуру сайта
            print("\n7. Исследование структуры сайта...")
            endpoints_to_test = [
                "/",
                "/profile",
                "/bookings",
                "/orders",
                "/tickets",
                "/account",
                "/dashboard"
            ]
            
            for endpoint in endpoints_to_test:
                try:
                    url = f"{auth_manager.base_url}{endpoint}"
                    response = auth_manager.session.get(url, timeout=10)
                    print(f"   {endpoint}: {response.status_code}")
                    if response.status_code == 200:
                        print(f"      ✅ Доступно: {response.url}")
                    elif response.status_code == 302:
                        print(f"      🔄 Перенаправление: {response.headers.get('Location', 'не указано')}")
                    else:
                        print(f"      ❌ Недоступно")
                except Exception as e:
                    print(f"   {endpoint}: ❌ Ошибка - {e}")
            
        else:
            print("❌ Не удалось выполнить вход")
            print("💡 Возможные причины:")
            print("   - Неверные учетные данные")
            print("   - Изменился механизм аутентификации сайта")
            print("   - Требуется капча или дополнительная проверка")
            print("   - Сайт заблокировал автоматические запросы")
            
            return False
    
    print("\n=== Тестирование завершено ===")
    return True


def main():
    """Основная функция"""
    print("🚀 Запуск тестирования с реальными данными")
    print("🔐 Будет использован реальный аккаунт для тестирования")
    
    # Основной тест
    success = test_real_auth()
    
    if success:
        print("\n🎉 Тестирование завершено успешно!")
        print("💡 Если получены реальные данные, можно интегрировать этот подход в AuthManager")
    else:
        print("\n😞 Тестирование выявило проблемы")
        print("💡 Возможно, потребуется использование Playwright для автоматизации браузера")


if __name__ == "__main__":
    main()
