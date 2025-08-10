#!/usr/bin/env python3
"""
Простой тест улучшенной системы авторизации
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from requests_auth import RequestsAuthManager
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_improved_auth():
    """Тест улучшенной системы авторизации"""
    print("🔧 Тест улучшенной системы авторизации")
    print("=" * 50)
    
    # Тестовые данные
    test_phone = "+375299605390"
    test_password = "Zxcvbnm,1"
    
    try:
        # Создаем менеджер
        print("📝 Создание менеджера авторизации...")
        auth_manager = RequestsAuthManager()
        
        print(f"🌐 Найден URL: {auth_manager.base_url}")
        
        # Тест валидации
        print("\n🔍 Тест валидации номера телефона:")
        phone_valid, phone_msg = auth_manager.validate_phone_number(test_phone)
        print(f"📱 Номер: {test_phone}")
        print(f"✅ Валидация: {'Успешно' if phone_valid else 'Ошибка'}")
        print(f"📄 Результат: {phone_msg}")
        
        if not phone_valid:
            print("❌ Валидация не пройдена, завершаем тест")
            return False
        
        # Тест входа
        print(f"\n🔐 Тест входа с номером: {phone_msg}")
        print("⏳ Выполняется вход...")
        
        login_success = auth_manager.login(test_phone, test_password)
        
        if login_success:
            print("✅ Вход успешен!")
            
            # Проверка авторизации
            print(f"🔓 Статус авторизации: {'✅' if auth_manager.is_authenticated else '❌'}")
            
            # Получение профиля
            print("\n👤 Получение данных профиля:")
            profile_result = auth_manager.get_profile()
            
            if profile_result['success']:
                print("✅ Профиль получен:")
                profile_data = profile_result['data']
                
                for key, value in profile_data.items():
                    print(f"  📋 {key}: {value}")
            else:
                print(f"❌ Ошибка получения профиля: {profile_result.get('error')}")
            
            # Получение билетов
            print("\n🎫 Получение билетов:")
            tickets = auth_manager.get_tickets()
            print(f"📊 Найдено билетов: {len(tickets)}")
            
            for i, ticket in enumerate(tickets[:3], 1):
                print(f"  🎟️ Билет {i}: {ticket}")
            
            return True
            
        else:
            print("❌ Вход не удался")
            print("🔧 Возможные причины:")
            print("  • Неверные учетные данные")
            print("  • Проблемы с сайтом")
            print("  • Сетевые ошибки")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False

if __name__ == "__main__":
    success = test_improved_auth()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("✅ Система авторизации готова к использованию")
        print("💡 Можно запускать бот: python src/improved_bot.py")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН")
        print("🔧 Требует дополнительной настройки")
    print("=" * 50)
