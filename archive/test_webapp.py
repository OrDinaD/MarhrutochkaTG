#!/usr/bin/env python3
"""
Тест веб-приложения функций
"""

from src.bot import create_webapp_url, create_webapp_keyboard

def test_webapp():
    print('=== Тест WebApp функций ===')
    
    # Тест создания URL
    url1 = create_webapp_url('minsk_ostrovets')
    url2 = create_webapp_url('ostrovets_minsk')  
    url3 = create_webapp_url('both')
    
    print(f'URL Минск->Островец: {url1}')
    print(f'URL Островец->Минск: {url2}')
    print(f'URL Оба направления: {url3}')
    
    # Тест создания клавиатуры
    keyboard1 = create_webapp_keyboard('minsk_ostrovets', '2025-07-28')
    keyboard2 = create_webapp_keyboard('both')
    
    print(f'Кнопок для Минск->Островец: {len(keyboard1.inline_keyboard)}')
    print(f'Кнопок для обоих направлений: {len(keyboard2.inline_keyboard)}')
    
    print('✅ WebApp тесты завершены')

if __name__ == "__main__":
    test_webapp()
