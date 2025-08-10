#!/usr/bin/env python3
"""
Тест системы авторизации
"""

from src.requests_auth import RequestsAuthManager

def test_auth():
    print('=== Тест системы авторизации ===')
    
    # Создаем менеджер
    auth_manager = RequestsAuthManager()
    
    print(f'Статус аутентификации: {auth_manager.is_authenticated}')
    print(f'URL сайта: {auth_manager.base_url}')
    
    # Тест получения профиля без аутентификации
    profile = auth_manager.get_profile()
    print(f'Профиль без аутентификации: {profile}')
    
    # Тест получения билетов без аутентификации
    tickets = auth_manager.get_tickets()
    print(f'Билеты без аутентификации: {len(tickets)} шт.')
    
    print('✅ Тесты авторизации завершены')

if __name__ == "__main__":
    test_auth()
