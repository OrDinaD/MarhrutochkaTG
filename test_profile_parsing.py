#!/usr/bin/env python3
"""
Тест улучшенного парсинга профиля
"""

import asyncio
import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth.improved_web_auth import ImprovedWebAuth
from dotenv import load_dotenv

load_dotenv()

# Настроим подробное логирование
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')

async def test_profile_parsing():
    """Тестирует парсинг профиля"""
    
    # Получаем данные из .env
    phone = os.getenv('DEFAULT_PHONE', '+375299605390')
    password = os.getenv('DEFAULT_PASSWORD', 'Zxcvbnm,1')
    
    print(f"🔐 Тестирую авторизацию с номером: {phone}")
    
    # Создаем экземпляр авторизации
    auth = ImprovedWebAuth()
    
    try:
        # Выполняем авторизацию
        print("📞 Выполняю авторизацию...")
        success = auth.login(phone, password)
        
        if success:
            print("✅ Авторизация успешна!")
            
            # Получаем профиль
            print("👤 Загружаю профиль...")
            profile = auth.get_user_profile()
            
            print(f"🔍 Результат get_user_profile(): {profile}")
            
            if profile:
                print("\n🎯 РЕЗУЛЬТАТ ПАРСИНГА ПРОФИЛЯ:")
                print(f"📝 Имя: '{profile.name}'")
                print(f"📝 Отчество: '{profile.patronymic}'") 
                print(f"📝 Фамилия: '{profile.surname}'")
                print(f"📧 Email: '{profile.email}'")
                print(f"📱 Телефон: '{profile.phone}'")
                print(f"🎂 Дата рождения: '{profile.birth_date}'")
                print(f"🆔 Серия паспорта: '{profile.passport_series}'")
                print(f"💳 Номер карточки: '{profile.card_number}'")
                
                # Формируем полное ФИО
                full_name_parts = []
                if profile.surname:
                    full_name_parts.append(profile.surname)
                if profile.name:
                    full_name_parts.append(profile.name)
                if profile.patronymic:
                    full_name_parts.append(profile.patronymic)
                
                full_name = " ".join(full_name_parts)
                print(f"\n✨ Полное ФИО: '{full_name}'")
                
                # Проверяем корректность
                expected_parts = ["Всилевский", "Владислав", "Валерьевич"]
                all_found = all(part in full_name for part in expected_parts)
                
                if all_found:
                    print("🎉 ТЕСТ ПРОЙДЕН! ФИО парсится корректно.")
                    return True
                else:
                    print("❌ ТЕСТ НЕ ПРОЙДЕН! Не все части ФИО найдены.")
                    return False
                    
            else:
                print("❌ Не удалось загрузить профиль")
                return False
                
        else:
            print("❌ Авторизация не удалась")
            return False
            
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_profile_parsing())
    sys.exit(0 if result else 1)
