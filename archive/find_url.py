#!/usr/bin/env python3
"""
Простой тест для определения правильного URL сайта
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from playwright.async_api import async_playwright

async def find_correct_url():
    """Поиск правильного URL сайта"""
    test_urls = [
        "https://marshrutochka.by",
        "https://bilet.marshrutochka.by",
        "https://www.marshrutochka.by",
        "https://online.marshrutochka.by",
        "https://билет.маршруточка.бел",
        "http://marshrutochka.by",
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        for url in test_urls:
            try:
                print(f"🔍 Проверяем: {url}")
                response = await page.goto(url, wait_until='networkidle', timeout=10000)
                
                if response and response.status == 200:
                    title = await page.title()
                    current_url = page.url
                    
                    print(f"✅ Успешно! URL: {current_url}")
                    print(f"📝 Заголовок: {title}")
                    
                    # Проверяем наличие формы входа
                    phone_input = await page.query_selector('input[name="phone"], input[type="tel"], input[placeholder*="телефон"]')
                    password_input = await page.query_selector('input[name="password"], input[type="password"]')
                    
                    if phone_input and password_input:
                        print("🔐 Найдена форма входа!")
                        await browser.close()
                        return current_url
                    else:
                        print("⚠️ Форма входа не найдена")
                else:
                    print(f"❌ Статус: {response.status if response else 'нет ответа'}")
                    
            except Exception as e:
                print(f"❌ Ошибка: {str(e)[:100]}")
                continue
        
        await browser.close()
        return None

if __name__ == "__main__":
    result = asyncio.run(find_correct_url())
    if result:
        print(f"\n🎉 Найден рабочий URL: {result}")
    else:
        print("\n❌ Рабочий URL не найден")
