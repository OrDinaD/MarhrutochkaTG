#!/usr/bin/env python3
"""
Прямое исследование API buspro.by
Тестируем endpoints напрямую через HTTP запросы
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BusproAPIDirectScanner:
    """Прямой сканер API buspro.by"""

    API_BASE = "https://buspro.by/api"
    COMPANY_ID = "35"
    
    def __init__(self):
        self.session: aiohttp.ClientSession = None
        self.results: Dict[str, Any] = {}
        
    async def start(self):
        self.session = aiohttp.ClientSession()
        logger.info("Сессия создана")
        
    async def stop(self):
        if self.session:
            await self.session.close()
        logger.info("Сессия закрыта")
        
    async def test_endpoint(self, endpoint: str, params: Dict = None) -> Dict:
        """Тестирование одного endpoint"""
        url = f"{self.API_BASE}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                result = {
                    'url': url,
                    'status': response.status,
                    'headers': dict(response.headers),
                    'body': None,
                    'error': None
                }
                
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type.lower():
                        result['body'] = await response.json()
                    else:
                        text = await response.text()
                        result['body'] = text[:500]  # Первые 500 символов
                else:
                    result['error'] = await response.text()
                    
                return result
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'status': None,
                'body': None
            }
    
    async def scan_all_endpoints(self):
        """Сканирование всех endpoints"""
        await self.start()
        
        try:
            # 1. Тестируем базовые endpoints
            logger.info("=" * 60)
            logger.info("📡 Тестирование базовых endpoints")
            logger.info("=" * 60)
            
            endpoints_to_test = [
                # Основные
                ("/route", {"s[company_id]": self.COMPANY_ID}),
                ("/route", {"s[company_id]": self.COMPANY_ID, "s[city_departure_id]": "519"}),
                ("/options/get-used-options", {"company": self.COMPANY_ID}),
                ("/check/source-reservation", {"source": "web", "company": self.COMPANY_ID}),
                
                # Пробуем другие возможные endpoints
                ("/cities", None),
                ("/cities/list", None),
                ("/directions", None),
                ("/trips", None),
                ("/schedule", None),
                ("/routes", None),
            ]
            
            for endpoint, params in endpoints_to_test:
                logger.info(f"\n🔍 Тестирование: {endpoint}")
                if params:
                    logger.info(f"   Параметры: {params}")
                    
                result = await self.test_endpoint(endpoint, params)
                
                if result['status'] == 200:
                    logger.info(f"   ✅ Успех! Status: {result['status']}")
                    if isinstance(result['body'], dict):
                        logger.info(f"   Keys: {list(result['body'].keys())}")
                    elif isinstance(result['body'], list):
                        logger.info(f"   Array length: {len(result['body'])}")
                else:
                    logger.info(f"   ❌ Ошибка: {result['status']} - {result.get('error', 'N/A')[:100]}")
                
                self.results[endpoint] = result
                await asyncio.sleep(0.5)  # Небольшая задержка между запросами
            
            # 2. Получаем список всех городов
            logger.info("\n" + "=" * 60)
            logger.info("🏙️ Получение списка городов")
            logger.info("=" * 60)
            
            cities_result = await self._get_all_cities()
            
            # 3. Тестируем поиск маршрутов между городами
            logger.info("\n" + "=" * 60)
            logger.info("🔍 Тестирование поиска маршрутов")
            logger.info("=" * 60)
            
            if cities_result.get('cities'):
                await self._test_route_search(cities_result['cities'])
            
            # 4. Генерируем документацию
            logger.info("\n" + "=" * 60)
            logger.info("📊 Генерация документации")
            logger.info("=" * 60)
            
            await self._generate_documentation(cities_result)
            
        finally:
            await self.stop()
    
    async def _get_all_cities(self) -> Dict:
        """Получение списка всех городов"""
        # Пробуем получить города через API
        cities = {}
        
        # Пробуем разные endpoints для получения городов
        city_endpoints = [
            "/cities",
            "/cities/list", 
            "/options/get-used-options",
        ]
        
        for endpoint in city_endpoints:
            try:
                result = await self.test_endpoint(endpoint, {"company": self.COMPANY_ID})
                if result['status'] == 200 and result['body']:
                    logger.info(f"Endpoint {endpoint} вернул данные")
                    if isinstance(result['body'], dict):
                        # Ищем города в ответе
                        for key, value in result['body'].items():
                            if isinstance(value, list) and len(value) > 0:
                                if isinstance(value[0], dict) and 'id' in value[0] and 'name' in value[0]:
                                    logger.info(f"   Найдены города в ключе: {key}")
                                    for city in value:
                                        cities[city['id']] = city['name']
            except Exception as e:
                logger.error(f"Ошибка при получении городов из {endpoint}: {e}")
        
        # Если не нашли через API, используем известные ID из старого сайта
        if not cities:
            logger.info("   Не найдены города через API, используем известные ID...")
            # Это примерный список, нужно уточнять
            known_cities = {
                "5": "Минск",
                "519": "Минск (альт.)",
                "520": "Островец", 
                "521": "Сморгонь",
                "522": "Ошмяны",
                "23": "Островец (стар.)",
                "24": "Ошмяны (стар.)",
                "22": "Сморгонь (стар.)",
            }
            cities = known_cities
        
        logger.info(f"   Всего городов: {len(cities)}")
        
        # Сохраняем
        cities_data = {'cities': cities}
        with open('scripts/responses/cities_direct.json', 'w', encoding='utf-8') as f:
            json.dump(cities_data, f, ensure_ascii=False, indent=2)
        logger.info("💾 Список городов сохранен")
        
        return cities_data
    
    async def _test_route_search(self, cities: Dict):
        """Тестирование поиска маршрутов"""
        # Тестовые маршруты
        test_routes = [
            ("5", "520", "Минск", "Островец"),
            ("520", "5", "Островец", "Минск"),
            ("5", "521", "Минск", "Сморгонь"),
            ("521", "5", "Сморгонь", "Минск"),
        ]
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        for from_id, to_id, from_name, to_name in test_routes:
            if from_id not in cities or to_id not in cities:
                logger.info(f"⏭️ Пропускаем {from_name} -> {to_name}")
                continue
                
            logger.info(f"\n🚌 {from_name} → {to_name} на {tomorrow}")
            
            # Пробуем разные форматы запросов
            search_params = [
                {
                    "s[company_id]": self.COMPANY_ID,
                    "s[city_departure_id]": from_id,
                    "s[city_arrival_id]": to_id,
                    "s[date]": tomorrow
                },
                {
                    "from": from_id,
                    "to": to_id,
                    "date": tomorrow
                }
            ]
            
            for i, params in enumerate(search_params):
                result = await self.test_endpoint("/trips/search", params)
                if result['status'] == 200:
                    logger.info(f"   ✅ Формат {i+1} успешен")
                    if isinstance(result['body'], dict):
                        logger.info(f"   Keys: {list(result['body'].keys())}")
                    break
                else:
                    logger.info(f"   ❌ Формат {i+1}: {result['status']}")
    
    async def _generate_documentation(self, cities_result: Dict):
        """Генерация документации"""
        doc = {
            'generated_at': datetime.now().isoformat(),
            'api_base': self.API_BASE,
            'company_id': self.COMPANY_ID,
            'endpoints': {},
            'cities': cities_result.get('cities', {}),
            'notes': []
        }
        
        # Анализируем результаты тестирования
        for endpoint, result in self.results.items():
            endpoint_info = {
                'url': result['url'],
                'status': result['status'],
                'success': result['status'] == 200,
                'response_keys': list(result['body'].keys()) if isinstance(result['body'], dict) else None,
                'sample_response': result['body'] if isinstance(result['body'], (dict, list)) else None
            }
            doc['endpoints'][endpoint] = endpoint_info
        
        # Добавляем заметки
        doc['notes'].append("API находится на внешнем домене buspro.by")
        doc['notes'].append("Требуется company_id=35 для всех запросов")
        doc['notes'].append("Некоторые endpoints могут требовать авторизации")
        
        # Сохраняем JSON
        with open('docs/buspro_api_direct.json', 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        logger.info("💾 Документация сохранена в docs/buspro_api_direct.json")
        
        # Генерируем Markdown
        self._generate_markdown(doc)
    
    def _generate_markdown(self, doc: Dict):
        """Генерация Markdown документации"""
        md = f"""# 🚌 API Документация BusPro.by

**Дата генерации:** {doc['generated_at']}

## Общая информация

- **API Base URL:** `{doc['api_base']}`
- **Company ID:** `{doc['company_id']}` (Маршруточка Плюс)

## 📡 Протестированные Endpoints

"""
        for endpoint, info in doc['endpoints'].items():
            status_icon = "✅" if info['success'] else "❌"
            md += f"""### {status_icon} `{endpoint}`

- **Status:** {info['status']}
- **URL:** `{info['url']}`
- **Response Keys:** {info['response_keys']}

"""
            if info['sample_response'] and isinstance(info['sample_response'], dict):
                md += f"""**Пример ответа:**
```json
{json.dumps(info['sample_response'], ensure_ascii=False, indent=2)[:1000]}...
```

"""
        
        md += f"""
## 🏙️ Города (ID → Название)

| ID | Город |
|----|-------|
"""
        for city_id, city_name in doc['cities'].items():
            md += f"| `{city_id}` | {city_name} |\n"
        
        md += f"""

## 📝 Заметки

"""
        for note in doc['notes']:
            md += f"- {note}\n"
        
        with open('docs/buspro_api_direct.md', 'w', encoding='utf-8') as f:
            f.write(md)
        logger.info("💾 Markdown документация сохранена в docs/buspro_api_direct.md")


async def main():
    scanner = BusproAPIDirectScanner()
    await scanner.scan_all_endpoints()
    logger.info("\n✅ Сканирование завершено!")


if __name__ == '__main__':
    asyncio.run(main())
