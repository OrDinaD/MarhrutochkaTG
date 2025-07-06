#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для тестирования входа в аккаунт напрямую через RequestsAuthManager
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.requests_auth import RequestsAuthManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_login(phone, password):
    """Тестирование входа в аккаунт"""
    logger.info(f"Тестирование входа для телефона {phone[:4]}****...")
    
    # Создаем экземпляр менеджера авторизации
    auth_manager = RequestsAuthManager()
    
    # Выполняем вход
    success = auth_manager.login(phone, password)
    
    if success:
        logger.info("✅ Вход выполнен успешно!")
        
        # Получаем данные профиля
        profile_data = auth_manager.get_profile()
        if profile_data:
            logger.info("✅ Профиль получен:")
            for key, value in profile_data.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.error("❌ Не удалось получить профиль")
        
        # Получаем билеты
        tickets = auth_manager.get_tickets()
        if tickets:
            logger.info(f"✅ Получено {len(tickets)} билетов:")
            for i, ticket in enumerate(tickets, 1):
                logger.info(f"  Билет #{i}:")
                for key, value in ticket.items():
                    logger.info(f"    {key}: {value}")
        else:
            logger.info("ℹ️ Билетов не найдено или не удалось получить данные")
        
        # Сохраняем сессию
        session_data = {
            'cookies': dict(auth_manager.session.cookies),
            'phone': phone,
            'is_authenticated': True
        }
        
        logger.info(f"Cookies: {json.dumps(dict(auth_manager.session.cookies), indent=2)}")
        
        return True
    else:
        logger.error("❌ Не удалось выполнить вход")
        return False

def main():
    """Основная функция"""
    print("=== Тест входа в аккаунт маршруточки ===")
    phone = input("Введите номер телефона: ")
    password = input("Введите пароль: ")
    
    test_login(phone, password)

if __name__ == "__main__":
    main()
