#!/usr/bin/env python3
"""
Получение реального HTML профиля
"""

import asyncio
import sys
import os
import logging
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth.improved_web_auth import ImprovedWebAuth
from dotenv import load_dotenv

load_dotenv()

async def debug_html():
    """Получает и анализирует реальный HTML"""
    
    # Получаем данные из .env
    phone = os.getenv('DEFAULT_PHONE', '+375299605390')
    password = os.getenv('DEFAULT_PASSWORD', 'Zxcvbnm,1')
    
    print(f"🔐 Авторизуюсь с номером: {phone}")
    
    # Создаем экземпляр авторизации
    auth = ImprovedWebAuth()
    
    try:
        # Выполняем авторизацию
        success = auth.login(phone, password)
        
        if success:
            print("✅ Авторизация успешна!")
            
            # Получаем HTML профиля
            profile_url = f"{auth.base_url}/profile"
            response = auth.session.get(profile_url)
            html = response.text
            
            print(f"📄 Размер HTML: {len(html)} символов")
            
            # Сохраняем HTML в файл для анализа
            with open('profile_debug.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("💾 HTML сохранен в profile_debug.html")
            
            # Ищем input поля с данными
            print("\n🔍 ПОИСК INPUT ПОЛЕЙ:")
            
            # Ищем все input поля
            input_pattern = r'<input[^>]*>'
            inputs = re.findall(input_pattern, html, re.IGNORECASE)
            
            for i, inp in enumerate(inputs):
                if any(word in inp.lower() for word in ['имя', 'фамилия', 'отчество', 'email', 'телефон', 'рождения']):
                    print(f"  {i+1}. {inp}")
            
            # Ищем данные в JavaScript
            print("\n🔍 ПОИСК В JAVASCRIPT:")
            js_pattern = r'window\.[^=]*=\s*[^;]*;'
            js_vars = re.findall(js_pattern, html)
            for js_var in js_vars:
                if any(word in js_var.lower() for word in ['user', 'profile', 'data']):
                    print(f"  {js_var}")
            
            # Ищем JSON данные
            print("\n🔍 ПОИСК JSON ДАННЫХ:")
            json_pattern = r'\{[^{}]*"[^"]*"[^{}]*:[^{}]*\}'
            json_blocks = re.findall(json_pattern, html)
            for json_block in json_blocks:
                if any(word in json_block.lower() for word in ['владислав', 'email', 'phone']):
                    print(f"  {json_block}")
            
            # Поиск специфических значений
            print(f"\n🔍 ПОИСК КОНКРЕТНЫХ ЗНАЧЕНИЙ:")
            if 'Владислав' in html:
                context_start = html.find('Владислав') - 100
                context_end = html.find('Владислав') + 100
                context = html[max(0, context_start):context_end]
                print(f"  'Владислав' найден в контексте: ...{context}...")
                
            if 'Всилевский' in html:
                context_start = html.find('Всилевский') - 100
                context_end = html.find('Всилевский') + 100
                context = html[max(0, context_start):context_end]
                print(f"  'Всилевский' найден в контексте: ...{context}...")
                
            if 'Валерьевич' in html:
                context_start = html.find('Валерьевич') - 100
                context_end = html.find('Валерьевич') + 100
                context = html[max(0, context_start):context_end]
                print(f"  'Валерьевич' найден в контексте: ...{context}...")
            
        else:
            print("❌ Авторизация не удалась")
            
    except Exception as e:
        print(f"💥 Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(debug_html())
