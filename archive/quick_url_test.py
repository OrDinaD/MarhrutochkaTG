#!/usr/bin/env python3
"""
Быстрый тест URL'ов сайта
"""

import requests
import time

def test_urls():
    """Быстрая проверка URL'ов"""
    test_urls = [
        "https://marshrutochka.by",
        "https://bilet.marshrutochka.by",
        "https://www.marshrutochka.by",
        "http://marshrutochka.by",
        "https://online.marshrutochka.by"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    })
    
    for url in test_urls:
        try:
            print(f"🔍 Проверяем: {url}")
            start_time = time.time()
            response = session.get(url, timeout=10, allow_redirects=True)
            end_time = time.time()
            
            if response.status_code == 200:
                print(f"✅ Успешно! Статус: {response.status_code}, Время: {end_time - start_time:.2f}с")
                print(f"🔗 Финальный URL: {response.url}")
                
                # Проверяем содержимое
                content = response.text.lower()
                if any(keyword in content for keyword in ['маршруточка', 'билет', 'marshrutochka', 'login', 'phone']):
                    print("📄 Содержимое выглядит правильно")
                    
                    # Ищем форму входа
                    if 'input' in content and ('phone' in content or 'password' in content):
                        print("🔐 Найдена форма входа!")
                        return url
                    else:
                        print("⚠️ Форма входа не найдена")
                else:
                    print("❌ Содержимое не соответствует ожидаемому")
            else:
                print(f"❌ Статус: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ошибка: {str(e)[:50]}...")
        
        print()
    
    return None

if __name__ == "__main__":
    print("🚀 Быстрый тест URL'ов сайта")
    working_url = test_urls()
    
    if working_url:
        print(f"🎉 Найден рабочий URL: {working_url}")
    else:
        print("❌ Рабочий URL не найден")
