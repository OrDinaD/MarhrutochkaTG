#!/usr/bin/env python3
"""
Скрипт для исследования API buspro.by
Анализирует все endpoints и сохраняет документацию
"""

import asyncio
import json
import logging
from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict, Any
from datetime import datetime, timedelta
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BusproAPIScanner:
    """Сканер для исследования API buspro.by"""

    FRONTEND_URL = "https://xn--80aa3afbnjeapfl8cj3h.xn--90ais/"
    API_BASE = "https://buspro.by/api"
    COMPANY_ID = "35"  # ID компании маршруточка
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Browser = None
        self.page: Page = None
        self.api_responses: Dict[str, Dict] = {}
        
    async def start(self):
        """Запуск браузера"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        
        # Перехват ответов API
        self.page.on("response", self._on_response)
        
        logger.info("Браузер запущен")
        
    async def stop(self):
        """Остановка браузера"""
        if self.browser:
            await self.browser.close()
        logger.info("Браузер остановлен")
        
    def _on_response(self, response):
        """Перехват ответов API"""
        url = response.url
        status = response.status
        
        # Фильтруем только API buspro.by
        if self.API_BASE in url:
            try:
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type.lower():
                    body = response.json()
                    self.api_responses[url] = {
                        'timestamp': datetime.now().isoformat(),
                        'url': url,
                        'status': status,
                        'headers': dict(response.headers),
                        'body': body
                    }
                    logger.info(f"📥 API RESPONSE: {status} {url}")
                    logger.info(f"   Body keys: {list(body.keys()) if isinstance(body, dict) else 'array[' + str(len(body)) + ']'}")
            except Exception as e:
                logger.error(f"Ошибка при получении ответа: {e}")
    
    async def explore_all_endpoints(self):
        """Исследование всех endpoints API"""
        await self.start()
        
        try:
            # 1. Загружаем главную страницу для инициализации API вызовов
            logger.info("=" * 60)
            logger.info("📄 Шаг 1: Загрузка главной страницы")
            logger.info("=" * 60)
            
            await self.page.goto(self.FRONTEND_URL, wait_until='networkidle')
            await self.page.wait_for_timeout(3000)
            
            # 2. Получаем список всех городов
            logger.info("\n" + "=" * 60)
            logger.info("🏙️ Шаг 2: Получение списка городов")
            logger.info("=" * 60)
            
            cities_data = await self._get_all_cities()
            
            # 3. Тестируем поиск маршрутов
            logger.info("\n" + "=" * 60)
            logger.info("🔍 Шаг 3: Тестирование поиска маршрутов")
            logger.info("=" * 60)
            
            search_results = await self._test_search_routes(cities_data)
            
            # 4. Генерируем документацию
            logger.info("\n" + "=" * 60)
            logger.info("📊 Шаг 4: Генерация документации API")
            logger.info("=" * 60)
            
            await self._generate_api_documentation(cities_data, search_results)
            
        finally:
            await self.stop()
            
    async def _get_all_cities(self) -> Dict:
        """Получение списка всех городов"""
        cities = {}
        
        # Пробуем получить города через evaluate
        try:
            # Ждем загрузки JS
            await self.page.wait_for_function("typeof window.reservationData !== 'undefined'", timeout=5000)
        except:
            logger.info("window.reservationData не найдено, пробуем другие методы...")
        
        # Получаем города из select элементов
        cities_from_select = await self.page.evaluate('''() => {
            const cities = { from: [], to: [] };
            document.querySelectorAll('select').forEach(select => {
                const options = [];
                select.querySelectorAll('option').forEach(option => {
                    if (option.value) {
                        options.push({
                            id: option.value,
                            name: option.text.trim()
                        });
                    }
                });
                if (select.id.includes('from') || select.name?.includes('from')) {
                    cities.from = options;
                } else if (select.id.includes('to') || select.name?.includes('to')) {
                    cities.to = options;
                }
            });
            return cities;
        }''')
        
        logger.info(f"Города из select from: {cities_from_select.get('from', [])}")
        logger.info(f"Города из select to: {cities_from_select.get('to', [])}")
        
        # Объединяем города
        all_cities = {}
        for city in cities_from_select.get('from', []) + cities_from_select.get('to', []):
            all_cities[city['id']] = city['name']
            
        cities['all'] = all_cities
        
        # Сохраняем
        with open('scripts/responses/cities.json', 'w', encoding='utf-8') as f:
            json.dump(cities, f, ensure_ascii=False, indent=2)
        logger.info("💾 Список городов сохранен в scripts/responses/cities.json")
        
        return cities
        
    async def _test_search_routes(self, cities_data: Dict) -> Dict:
        """Тестирование поиска маршрутов"""
        results = {}
        
        cities = cities_data.get('all', {})
        
        # Основные города для теста
        test_routes = [
            ("520", "5", "Островец", "Минск"),    # Островец -> Минск
            ("5", "520", "Минск", "Островец"),     # Минск -> Островец
            ("521", "5", "Сморгонь", "Минск"),     # Сморгонь -> Минск
            ("5", "521", "Минск", "Сморгонь"),     # Минск -> Сморгонь
        ]
        
        # Дата завтра
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
        
        for from_id, to_id, from_name, to_name in test_routes:
            if from_id not in cities or to_id not in cities:
                logger.info(f"⏭️ Пропускаем {from_name} -> {to_name} (города не найдены)")
                continue
                
            logger.info(f"\n🔍 Поиск: {from_name} -> {to_name} на {tomorrow}")
            
            result = await self._search_route(from_id, to_id, tomorrow)
            results[f"{from_id}_{to_id}"] = {
                'from': from_name,
                'to': to_name,
                'date': tomorrow,
                'result': result
            }
            
            await self.page.wait_for_timeout(2000)
            
        # Сохраняем результаты
        with open('scripts/responses/search_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info("\n💾 Результаты поиска сохранены в scripts/responses/search_results.json")
        
        return results
        
    async def _search_route(self, from_id: str, to_id: str, date: str) -> Dict:
        """Поиск маршрута"""
        try:
            # Переходим на главную
            await self.page.goto(self.FRONTEND_URL, wait_until='networkidle')
            await self.page.wait_for_timeout(2000)
            
            # Заполняем форму через JavaScript (так как select могут быть кастомными)
            await self.page.evaluate(f'''() => {{
                // Находим select и выбираем значения
                const fromSelect = document.querySelector('select[name="city_from_id"]') || 
                                   document.querySelector('select[id*="from"]') ||
                                   document.querySelectorAll('select')[0];
                const toSelect = document.querySelector('select[name="city_to_id"]') || 
                                document.querySelector('select[id*="to"]') ||
                                document.querySelectorAll('select')[1];
                const dateInput = document.querySelector('input[name="date"]') ||
                                 document.querySelector('input[type="text"]');
                
                if (fromSelect) {{
                    fromSelect.value = "{from_id}";
                    fromSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                
                if (toSelect) {{
                    toSelect.value = "{to_id}";
                    toSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                
                if (dateInput) {{
                    dateInput.value = "{date}";
                    dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}''')
            
            await self.page.wait_for_timeout(1000)
            
            # Кликаем кнопку поиска
            search_button = await self.page.query_selector(
                'button[type="submit"], button.js_search-button, button:has-text("Найти"), button:has-text("Поиск")'
            )
            
            if search_button:
                await search_button.click()
                logger.info("   Кнопка поиска нажата")
            else:
                logger.info("   Кнопка поиска не найдена, пробуем найти по тексту...")
                buttons = await self.page.query_selector_all('button')
                for btn in buttons:
                    text = await btn.inner_text()
                    if 'найти' in text.lower() or 'поиск' in text.lower() or 'search' in text.lower():
                        await btn.click()
                        logger.info(f"   Найдена кнопка: {text}")
                        break
            
            # Ждем загрузки результатов
            await self.page.wait_for_timeout(5000)
            
            # Скриншот
            await self.page.screenshot(path=f'scripts/responses/search_{from_id}_{to_id}.png')
            
            # Получаем HTML результатов
            html = await self.page.content()
            with open(f'scripts/responses/search_{from_id}_{to_id}.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            # Пробуем извлечь результаты через evaluate
            search_result = await self.page.evaluate('''() => {
                const result = {
                    routes: [],
                    raw_text: document.body.innerText.substring(0, 2000)
                };
                
                // Ищем блоки маршрутов
                document.querySelectorAll('[class*="route"], [class*="schedule"], [class*="trip"], [class*="bus"], [class*="nf-"]').forEach(el => {
                    result.routes.push({
                        tag: el.tagName,
                        classes: el.className,
                        id: el.id,
                        text: el.innerText.substring(0, 300)
                    });
                });
                
                return result;
            }''')
            
            return search_result
            
        except Exception as e:
            logger.error(f"Ошибка при поиске маршрута: {e}")
            return {'error': str(e)}
            
    async def _generate_api_documentation(self, cities_data: Dict, search_results: Dict):
        """Генерация документации API"""
        
        doc = {
            'generated_at': datetime.now().isoformat(),
            'api_base_url': self.API_BASE,
            'company_id': self.COMPANY_ID,
            'frontend_url': self.FRONTEND_URL,
            'endpoints': [],
            'cities': cities_data.get('all', {}),
            'data_structures': {}
        }
        
        # Анализируем перехваченные ответы
        for url, response_data in self.api_responses.items():
            endpoint = url.replace(self.API_BASE, '').split('?')[0]
            method = 'GET'  # По умолчанию
            
            endpoint_info = {
                'path': endpoint,
                'full_url': url,
                'method': method,
                'description': self._describe_endpoint(endpoint),
                'parameters': self._extract_parameters(url),
                'response_structure': self._analyze_response_structure(response_data.get('body', {})),
                'sample_response': response_data.get('body', {})
            }
            
            doc['endpoints'].append(endpoint_info)
            
        # Анализируем структуры данных из search_results
        for route_key, route_data in search_results.items():
            if 'result' in route_data and isinstance(route_data['result'], dict):
                routes = route_data['result'].get('routes', [])
                if routes:
                    doc['data_structures']['route'] = self._analyze_route_structure(routes[0])
                    break
        
        # Сохраняем документацию
        os.makedirs('docs', exist_ok=True)
        
        with open('docs/buspro_api_documentation.json', 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        logger.info("💾 Документация API сохранена в docs/buspro_api_documentation.json")
        
        # Генерируем Markdown версию
        self._generate_markdown_docs(doc)
        
    def _describe_endpoint(self, endpoint: str) -> str:
        """Описание endpoint на основе пути"""
        descriptions = {
            '/route': 'Получение маршрутов и направлений',
            '/options/get-used-options': 'Получение доступных опций и настроек',
            '/check/source-reservation': 'Проверка возможности бронирования',
            '/schedule': 'Получение расписания',
            '/trips': 'Поиск рейсов по датам',
            '/seats': 'Информация о местах',
            '/booking': 'Бронирование билетов',
            '/payment': 'Оплата билетов',
            '/orders': 'Информация о заказах пользователя',
        }
        
        for path, desc in descriptions.items():
            if path in endpoint:
                return desc
                
        return 'API endpoint'
        
    def _extract_parameters(self, url: str) -> Dict:
        """Извлечение параметров из URL"""
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Преобразуем в более читаемый формат
        result = {}
        for key, values in params.items():
            result[key] = {
                'type': 'string',
                'example': values[0] if values else None,
                'required': True
            }
            
        return result
        
    def _analyze_response_structure(self, body: Any, depth: int = 0) -> Dict:
        """Анализ структуры ответа"""
        if depth > 3:
            return {'type': 'object', 'description': 'Max depth reached'}
            
        if isinstance(body, dict):
            structure = {'type': 'object', 'properties': {}}
            for key, value in body.items():
                structure['properties'][key] = self._analyze_response_structure(value, depth + 1)
            return structure
        elif isinstance(body, list):
            if body:
                return {
                    'type': 'array',
                    'items': self._analyze_response_structure(body[0], depth + 1),
                    'length': len(body)
                }
            return {'type': 'array', 'items': {}}
        else:
            return {
                'type': type(body).__name__,
                'example': body if isinstance(body, (str, int, float, bool)) else None
            }
            
    def _analyze_route_structure(self, route: Dict) -> Dict:
        """Анализ структуры маршрута"""
        return {
            'type': 'object',
            'description': 'Структура маршрута/рейса',
            'properties': {
                key: {'type': type(value).__name__} 
                for key, value in route.items()
            }
        }
        
    def _generate_markdown_docs(self, doc: Dict):
        """Генерация Markdown документации"""
        
        md = f"""# 🚌 API Документация BusPro (Маршруточка)

**Сгенерировано:** {doc['generated_at']}

## Общая информация

- **Base URL:** `{doc['api_base_url']}`
- **Company ID:** `{doc['company_id']}`
- **Frontend:** `{doc['frontend_url']}`

## 🔌 Endpoints

"""
        
        for endpoint in doc['endpoints']:
            md += f"""### {endpoint['method']} `{endpoint['path']}`

{endpoint['description']}

**Full URL:** `{endpoint['full_url']}`

**Параметры:**
"""
            for param, info in endpoint['parameters'].items():
                md += f"- `{param}` ({info['type']}) - Пример: `{info['example']}`\n"
            
            md += f"""
**Структура ответа:**
```json
{json.dumps(endpoint['sample_response'], ensure_ascii=False, indent=2)[:1000]}...
```

---

"""
        
        md += """## 🏙️ Города

| ID | Название |
|----|----------|
"""
        for city_id, city_name in doc['cities'].items():
            md += f"| {city_id} | {city_name} |\n"
        
        with open('docs/buspro_api_documentation.md', 'w', encoding='utf-8') as f:
            f.write(md)
        logger.info("💾 Markdown документация сохранена в docs/buspro_api_documentation.md")


async def main():
    scanner = BusproAPIScanner(headless=False)
    await scanner.explore_all_endpoints()
    logger.info("\n✅ Исследование API завершено!")


if __name__ == '__main__':
    asyncio.run(main())
