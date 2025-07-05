#!/usr/bin/env python3
"""
Тестирование RequestsAuthManager с реальными данными
"""

import os
import sys
import json
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from requests_auth import RequestsAuthManager


def test_requests_auth():
    """Тест аутентификации через requests"""
    print("=== Тестирование RequestsAuthManager ===")
    
    # Получаем данные для входа из переменных окружения
    username = os.getenv('MARSHRUT_USERNAME', 'demo_user')
    password = os.getenv('MARSHRUT_PASSWORD', 'demo_password')
    
    if username == 'demo_user':
        print("⚠️  Используются демо-данные для входа")
        print("💡 Для реального тестирования установите переменные окружения:")
        print("   export MARSHRUT_USERNAME='your_username'")
        print("   export MARSHRUT_PASSWORD='your_password'")
        print()
    
    # Создаем менеджер аутентификации
    with RequestsAuthManager() as auth_manager:
        print("1. Создан RequestsAuthManager")
        
        # Тест получения страницы входа
        print("\n2. Тестирование получения страницы входа...")
        success, csrf_token = auth_manager.get_login_page()
        if success:
            print(f"✅ Страница входа получена, CSRF токен: {csrf_token[:10] if csrf_token else 'не найден'}...")
            print(f"📊 Cookies: {dict(auth_manager.session.cookies)}")
        else:
            print("❌ Не удалось получить страницу входа")
            return False
        
        # Тест входа
        print(f"\n3. Тестирование входа с пользователем: {username}")
        login_success = auth_manager.login(username, password)
        
        if login_success:
            print("✅ Вход выполнен успешно!")
            print(f"📊 Cookies после входа: {dict(auth_manager.session.cookies)}")
            
            # Тест получения профиля
            print("\n4. Тестирование получения профиля...")
            profile_result = auth_manager.get_profile_info()
            
            if profile_result['success']:
                print("✅ Профиль получен!")
                print(f"📊 URL профиля: {profile_result.get('url', 'не указан')}")
                print("📋 Данные профиля:")
                print(json.dumps(profile_result['data'], indent=2, ensure_ascii=False))
            else:
                print(f"❌ Не удалось получить профиль: {profile_result.get('error', 'неизвестная ошибка')}")
            
            # Тест получения бронирований
            print("\n5. Тестирование получения бронирований...")
            bookings_result = auth_manager.get_bookings()
            
            if bookings_result['success']:
                print("✅ Бронирования получены!")
                print(f"📊 URL бронирований: {bookings_result.get('url', 'не указан')}")
                print(f"📋 Количество бронирований: {len(bookings_result['bookings'])}")
                
                for i, booking in enumerate(bookings_result['bookings'], 1):
                    print(f"\n   📋 Бронирование {i}:")
                    print(json.dumps(booking, indent=4, ensure_ascii=False))
                    
            else:
                print(f"❌ Не удалось получить бронирования: {bookings_result.get('error', 'неизвестная ошибка')}")
            
        else:
            print("❌ Не удалось выполнить вход")
            print("💡 Возможные причины:")
            print("   - Неверные учетные данные")
            print("   - Изменился механизм аутентификации сайта")
            print("   - Проблемы с сетью")
            print("   - Сайт заблокировал запросы")
            
            return False
    
    print("\n=== Тестирование завершено ===")
    return True


def test_session_persistence():
    """Тест сохранения сессии"""
    print("\n=== Тестирование сохранения сессии ===")
    
    # Создаем менеджер и пытаемся сделать несколько запросов
    auth_manager = RequestsAuthManager()
    
    try:
        # Первый запрос
        print("1. Получение главной страницы...")
        response1 = auth_manager.session.get(auth_manager.base_url)
        print(f"   Статус: {response1.status_code}")
        print(f"   Cookies: {dict(auth_manager.session.cookies)}")
        
        # Второй запрос с теми же cookies
        print("\n2. Повторный запрос с сохраненными cookies...")
        response2 = auth_manager.session.get(auth_manager.base_url + "/login")
        print(f"   Статус: {response2.status_code}")
        print(f"   Cookies: {dict(auth_manager.session.cookies)}")
        
        # Проверяем, что cookies сохранились
        if len(auth_manager.session.cookies) > 0:
            print("✅ Cookies сохраняются между запросами")
        else:
            print("❌ Cookies не сохраняются")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании сессии: {e}")
    
    finally:
        auth_manager.close()


def main():
    """Основная функция"""
    print("🚀 Запуск тестирования requests-based аутентификации")
    print("🌐 Сайт: https://bilyet.marshrut.by")
    print()
    
    # Тест сохранения сессии
    test_session_persistence()
    
    # Основной тест
    success = test_requests_auth()
    
    if success:
        print("\n🎉 Тестирование завершено успешно!")
        print("💡 Если получены реальные данные, можно интегрировать этот подход в AuthManager")
    else:
        print("\n😞 Тестирование выявило проблемы")
        print("💡 Возможно, потребуется дополнительная настройка или использование браузерной автоматизации")


if __name__ == "__main__":
    main()
