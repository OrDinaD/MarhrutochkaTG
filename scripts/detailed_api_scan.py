#!/usr/bin/env python3
"""
Детальное исследование API buspro.by
Получение полной структуры маршрутов и городов
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BusproAPIDetailedScanner:
    """Детальный сканер API"""

    API_BASE = "https://buspro.by/api"
    COMPANY_ID = "35"
    
    def __init__(self):
        self.session: aiohttp.ClientSession = None
        
    async def start(self):
        self.session = aiohttp.ClientSession()
        
    async def stop(self):
        if self.session:
            await self.session.close()
    
    async def get_routes(self, params: Dict = None) -> Any:
        """Получение списка маршрутов"""
        url = f"{self.API_BASE}/route"
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            return None
    
    async def get_options(self) -> Dict:
        """Получение опций"""
        url = f"{self.API_BASE}/options/get-used-options"
        async with self.session.get(url, params={"company": self.COMPANY_ID}) as response:
            if response.status == 200:
                return await response.json()
            return None
    
    async def analyze_route_structure(self, route: Dict, index: int):
        """Анализ структуры одного маршрута"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Маршрут #{index+1}")
        logger.info(f"{'='*60}")
        
        for key, value in route.items():
            if isinstance(value, dict):
                logger.info(f"📁 {key}: (object)")
                for k, v in value.items():
                    logger.info(f"   └─ {k}: {type(v).__name__} = {str(v)[:100]}")
            elif isinstance(value, list):
                logger.info(f"📦 {key}: (array[{len(value)}])")
                if value and isinstance(value[0], dict):
                    logger.info(f"   └─ [{len(value)} objects]")
                    for i, item in enumerate(value[:2]):
                        logger.info(f"      [{i}]: {json.dumps(item, ensure_ascii=False)[:200]}...")
            else:
                logger.info(f"📄 {key}: {type(value).__name__} = {str(value)[:200]}")
    
    async def scan(self):
        """Основное сканирование"""
        await self.start()
        
        try:
            # 1. Получаем все маршруты компании
            logger.info("=" * 60)
            logger.info("📡 Получение всех маршрутов компании")
            logger.info("=" * 60)
            
            routes = await self.get_routes({"s[company_id]": self.COMPANY_ID})
            
            if routes and isinstance(routes, list):
                logger.info(f"✅ Найдено маршрутов: {len(routes)}")
                
                # Анализируем первый маршрут детально
                if routes:
                    await self.analyze_route_structure(routes[0], 0)
                
                # Извлекаем все города из маршрутов
                logger.info("\n" + "=" * 60)
                logger.info("🏙️ Извлечение городов из маршрутов")
                logger.info("=" * 60)
                
                cities = {}
                for route in routes:
                    # cityDeparture и cityArrival
                    if 'cityDeparture' in route:
                        cd = route['cityDeparture']
                        if isinstance(cd, dict) and 'id' in cd:
                            cities[str(cd['id'])] = cd.get('name', 'Unknown')
                    
                    if 'cityArrival' in route:
                        ca = route['cityArrival']
                        if isinstance(ca, dict) and 'id' in ca:
                            cities[str(ca['id'])] = ca.get('name', 'Unknown')
                    
                    # points
                    if 'points' in route and isinstance(route['points'], list):
                        for point in route['points']:
                            if isinstance(point, dict) and 'city' in point:
                                city = point['city']
                                if isinstance(city, dict) and 'id' in city:
                                    cities[str(city['id'])] = city.get('name', 'Unknown')
                
                logger.info(f"   Всего уникальных городов: {len(cities)}")
                for city_id, city_name in sorted(cities.items()):
                    logger.info(f"   {city_id}: {city_name}")
                
                # Сохраняем города
                with open('docs/buspro_cities.json', 'w', encoding='utf-8') as f:
                    json.dump(cities, f, ensure_ascii=False, indent=2)
                logger.info("\n💾 Города сохранены в docs/buspro_cities.json")
                
                # 2. Получаем маршруты для конкретного города отправления
                logger.info("\n" + "=" * 60)
                logger.info("📡 Получение маршрутов из Минска (city_departure_id=519)")
                logger.info("=" * 60)
                
                minsk_routes = await self.get_routes({
                    "s[company_id]": self.COMPANY_ID,
                    "s[city_departure_id]": "519"
                })
                
                if minsk_routes and isinstance(minsk_routes, list):
                    logger.info(f"✅ Найдено маршрутов из Минска: {len(minsk_routes)}")
                    
                    # Анализируем структуру
                    if minsk_routes:
                        await self.analyze_route_structure(minsk_routes[0], 0)
                
                # 3. Сохраняем полные данные маршрутов
                logger.info("\n" + "=" * 60)
                logger.info("💾 Сохранение полных данных")
                logger.info("=" * 60)
                
                with open('docs/buspro_routes_all.json', 'w', encoding='utf-8') as f:
                    json.dump(routes, f, ensure_ascii=False, indent=2)
                logger.info("💾 Все маршруты сохранены в docs/buspro_routes_all.json")
                
                with open('docs/buspro_routes_minsk.json', 'w', encoding='utf-8') as f:
                    json.dump(minsk_routes, f, ensure_ascii=False, indent=2)
                logger.info("💾 Маршруты из Минска сохранены в docs/buspro_routes_minsk.json")
                
                # 4. Генерируем документацию
                self._generate_full_documentation(routes, minsk_routes, cities)
                
            else:
                logger.error("❌ Не удалось получить маршруты")
                
        finally:
            await self.stop()
    
    def _generate_full_documentation(self, routes, minsk_routes, cities):
        """Генерация полной документации"""
        
        # Анализируем структуру ответа
        sample_route = routes[0] if routes else {}
        
        doc = f"""# 🚌 Полная документация API BusPro.by

**Дата генерации:** {datetime.now().isoformat()}

## Общая информация

- **API Base URL:** `{self.API_BASE}`
- **Company ID:** `{self.COMPANY_ID}` (Маршруточка Плюс)

## 📡 Рабочие Endpoints

### GET /route

Получение списка маршрутов компании.

**Параметры:**
| Параметр | Обязательный | Описание | Пример |
|----------|--------------|----------|--------|
| `s[company_id]` | ✅ | ID компании | `35` |
| `s[city_departure_id]` | ❌ | ID города отправления | `519` |

**Пример запроса:**
```
GET https://buspro.by/api/route?s[company_id]=35
GET https://buspro.by/api/route?s[company_id]=35&s[city_departure_id]=519
```

**Структура ответа:**
```json
{json.dumps(sample_route, ensure_ascii=False, indent=2)[:2000]}...
```

### GET /options/get-used-options

Получение настроек и опций системы.

**Параметры:**
| Параметр | Обязательный | Описание | Пример |
|----------|--------------|----------|--------|
| `company` | ✅ | ID компании | `35` |

**Пример запроса:**
```
GET https://buspro.by/api/options/get-used-options?company=35
```

**Пример ответа:**
```json
{{
  "usePoints": false,
  "useWebPay": false,
  "usePromocode": false,
  "useSeating": false,
  "useFinishStay": true,
  "notPhoneMask": false,
  "international": false,
  "cancelReservationLimit": {{
    "status": false,
    "period": 0
  }}
}}
```

### GET /check/source-reservation

Проверка возможности бронирования.

**Параметры:**
| Параметр | Обязательный | Описание | Пример |
|----------|--------------|----------|--------|
| `source` | ✅ | Источник | `web` |
| `company` | ✅ | ID компании | `35` |

**Пример запроса:**
```
GET https://buspro.by/api/check/source-reservation?source=web&company=35
```

## 🏙️ Города

| ID | Название |
|----|----------|
"""
        
        for city_id, city_name in sorted(cities.items(), key=lambda x: x[1]):
            doc += f"| `{city_id}` | {city_name} |\n"
        
        doc += f"""

## 📊 Структура данных маршрута

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | ID маршрута |
| `name` | string | Название маршрута |
| `cityDeparture` | object | Город отправления |
| `cityArrival` | object | Город прибытия |
| `points` | array | Промежуточные точки |
| `directions` | array | Направления/рейсы |

### Структура cityDeparture/cityArrival:

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | ID города |
| `name` | string | Название города |
| `address` | string | Адрес (опционально) |

### Структура points:

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | ID точки |
| `time` | string | Время прибытия |
| `city` | object | Информация о городе |

## 🔍 Как искать рейсы

1. Получить список маршрутов через `/route`
2. Найти нужный маршрут по городам
3. Использовать `directions` для получения расписания
4. Выбрать подходящий рейс по времени

## 📝 Заметки

- API не требует авторизации для чтения
- Все даты в формате `YYYY-MM-DD`
- Все времена в формате `HH:MM`
- Компания ID `35` = Маршруточка Плюс
"""
        
        with open('docs/buspro_api_full.md', 'w', encoding='utf-8') as f:
            f.write(doc)
        
        logger.info("💾 Полная документация сохранена в docs/buspro_api_full.md")


async def main():
    scanner = BusproAPIDetailedScanner()
    await scanner.scan()
    logger.info("\n✅ Детальное сканирование завершено!")


if __name__ == '__main__':
    asyncio.run(main())
