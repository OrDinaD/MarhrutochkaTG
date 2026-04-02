#!/usr/bin/env python3
"""
Скрипт для сканирования нового сайта маршруточка.бел через Playwright
Собирает информацию о структуре API, endpoints, параметрах запросов
"""

import asyncio
import json
import logging
from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SiteScanner:
    """Сканер для анализа структуры сайта"""

    NEW_SITE_URL = "https://xn--80aa3afbnjeapfl8cj3h.xn--90ais/"
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Browser = None
        self.page: Page = None
        self.api_requests: List[Dict] = []
        self.api_responses: List[Dict] = []
        
    async def start(self):
        """Запуск браузера"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        
        # Перехват запросов
        self.page.on("request", self._on_request)
        self.page.on("response", self._on_response)
        
        logger.info("Браузер запущен")
        
    async def stop(self):
        """Остановка браузера"""
        if self.browser:
            await self.browser.close()
        logger.info("Браузер остановлен")
        
    def _on_request(self, request):
        """Перехват запросов"""
        url = request.url
        method = request.method
        post_data = request.post_data
        
        # Фильтруем только API запросы (не статику)
        if not any(ext in url for ext in ['.png', '.jpg', '.jpeg', '.gif', '.css', '.woff', '.woff2', '.ttf', '.svg']):
            request_info = {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'method': method,
                'headers': dict(request.headers),
                'post_data': post_data
            }
            self.api_requests.append(request_info)
            logger.info(f"📤 REQUEST: {method} {url}")
            if post_data:
                logger.info(f"   POST data: {post_data[:200]}...")
    
    def _on_response(self, response):
        """Перехват ответов"""
        url = response.url
        status = response.status
        
        # Фильтруем только API ответы
        if not any(ext in url for ext in ['.png', '.jpg', '.jpeg', '.gif', '.css', '.woff', '.woff2', '.ttf', '.svg']):
            try:
                response_info = {
                    'timestamp': datetime.now().isoformat(),
                    'url': url,
                    'status': status,
                    'headers': dict(response.headers),
                }
                
                # Пробуем получить JSON
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type.lower():
                    try:
                        response_info['body'] = response.json()
                    except:
                        response_info['body'] = response.text()[:500]
                else:
                    response_info['body'] = response.text()[:500]
                    
                self.api_responses.append(response_info)
                logger.info(f"📥 RESPONSE: {status} {url}")
            except Exception as e:
                logger.error(f"Ошибка при получении ответа: {e}")
    
    async def scan_main_page(self):
        """Сканирование главной страницы"""
        logger.info("=" * 60)
        logger.info("📄 Сканирование главной страницы...")
        logger.info("=" * 60)
        
        await self.page.goto(self.NEW_SITE_URL, wait_until='networkidle')
        await self.page.wait_for_timeout(3000)
        
        # Скриншот
        await self.page.screenshot(path='scripts/screenshots/main_page.png')
        logger.info("📸 Скриншот главной страницы сохранен")
        
        # Получаем HTML
        html = await self.page.content()
        with open('scripts/responses/main_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info("💾 HTML главной страницы сохранен")
        
        # Анализируем структуру
        await self._analyze_page_structure()
        
    async def _analyze_page_structure(self):
        """Анализ структуры страницы"""
        logger.info("\n🔍 Анализ структуры страницы...")
        
        # Заголовки
        titles = await self.page.query_selector_all('h1, h2, h3')
        logger.info(f"   Найдено заголовков: {len(titles)}")
        for i, title in enumerate(titles[:5]):
            text = await title.inner_text()
            tag = await title.evaluate('el => el.tagName')
            logger.info(f"   - {tag}: {text[:100]}")
        
        # Формы
        forms = await self.page.query_selector_all('form')
        logger.info(f"   Найдено форм: {len(forms)}")
        
        # Кнопки
        buttons = await self.page.query_selector_all('button, input[type="submit"]')
        logger.info(f"   Найдено кнопок: {len(buttons)}")
        
        # Selects (выпадающие списки)
        selects = await self.page.query_selector_all('select')
        logger.info(f"   Найдено select: {len(selects)}")
        
        # Inputs
        inputs = await self.page.query_selector_all('input')
        logger.info(f"   Найдено input: {len(inputs)}")
        
        # Ссылки
        links = await self.page.query_selector_all('a[href]')
        logger.info(f"   Найдено ссылок: {len(links)}")
        
        # Получаем все города из select
        await self._extract_cities()
        
    async def _extract_cities(self):
        """Извлечение списка городов"""
        logger.info("\n🏙️ Извлечение списка городов...")
        
        cities = await self.page.evaluate('''() => {
            const cities = {};
            document.querySelectorAll('select').forEach(select => {
                const selectName = select.name || select.id || 'unknown';
                cities[selectName] = [];
                select.querySelectorAll('option').forEach(option => {
                    if (option.value) {
                        cities[selectName].push({
                            value: option.value,
                            text: option.text
                        });
                    }
                });
            });
            return cities;
        }''')
        
        logger.info(f"   Найдено городов в select: {json.dumps(cities, ensure_ascii=False, indent=2)}")
        
        with open('scripts/responses/cities.json', 'w', encoding='utf-8') as f:
            json.dump(cities, f, ensure_ascii=False, indent=2)
        logger.info("💾 Список городов сохранен")
        
    async def test_search(self, from_city: str = "5", to_city: str = "23", date: str = None):
        """Тестирование поиска маршрутов"""
        if date is None:
            from datetime import datetime, timedelta
            date = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
        
        logger.info("=" * 60)
        logger.info(f"🔍 Тестирование поиска: {from_city} -> {to_city} на {date}")
        logger.info("=" * 60)
        
        # Переходим на главную
        await self.page.goto(self.NEW_SITE_URL, wait_until='networkidle')
        await self.page.wait_for_timeout(2000)
        
        # Пробуем заполнить форму поиска
        try:
            # Выбираем город отправления
            logger.info(f"   Выбираем город отправления: {from_city}")
            await self.page.select_option('select[name="city_from_id"]', from_city)
            await self.page.wait_for_timeout(500)
            
            # Выбираем город назначения
            logger.info(f"   Выбираем город назначения: {to_city}")
            await self.page.select_option('select[name="city_to_id"]', to_city)
            await self.page.wait_for_timeout(500)
            
            # Заполняем дату
            logger.info(f"   Заполняем дату: {date}")
            await self.page.fill('input[name="date"]', date)
            await self.page.wait_for_timeout(500)
            
            # Кликаем кнопку поиска
            logger.info("   Кликаем кнопку поиска...")
            search_button = await self.page.query_selector('button.js_search-button, button[type="submit"], .search-button')
            if search_button:
                await search_button.click()
            else:
                # Пробуем найти по тексту
                buttons = await self.page.query_selector_all('button')
                for btn in buttons:
                    text = await btn.inner_text()
                    if 'поиск' in text.lower() or 'найти' in text.lower():
                        await btn.click()
                        break
            
            # Ждем загрузки результатов
            await self.page.wait_for_timeout(5000)
            
            # Скриншот результатов
            await self.page.screenshot(path='scripts/screenshots/search_results.png')
            logger.info("📸 Скриншот результатов поиска сохранен")
            
            # Сохраняем HTML
            html = await self.page.content()
            with open('scripts/responses/search_results.html', 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info("💾 HTML результатов поиска сохранен")
            
            # Анализируем результаты
            await self._analyze_search_results()
            
        except Exception as e:
            logger.error(f"Ошибка при тестировании поиска: {e}")
            
    async def _analyze_search_results(self):
        """Анализ результатов поиска"""
        logger.info("\n🔍 Анализ результатов поиска...")
        
        # Получаем структуру результатов
        result_structure = await self.page.evaluate('''() => {
            const results = {
                route_blocks: [],
                schedule_blocks: [],
                any_blocks: []
            };
            
            // Ищем блоки маршрутов
            document.querySelectorAll('[class*="route"], [class*="schedule"], [class*="trip"], [class*="bus"]').forEach(el => {
                results.any_blocks.push({
                    tag: el.tagName,
                    classes: el.className,
                    id: el.id,
                    text: el.innerText.substring(0, 200)
                });
            });
            
            return results;
        }''')
        
        logger.info(f"   Найдено блоков: {json.dumps(result_structure, ensure_ascii=False, indent=2)}")
        
    async def explore_api(self):
        """Исследование API через анализ network запросов"""
        logger.info("=" * 60)
        logger.info("🌐 Исследование API...")
        logger.info("=" * 60)
        
        # Переходим на главную
        await self.page.goto(self.NEW_SITE_URL, wait_until='networkidle')
        await self.page.wait_for_timeout(2000)
        
        # Открываем DevTools Network panel эмуляцию через console
        logger.info("\n📊 Перехваченные API запросы:")
        
        api_endpoints = {}
        for req in self.api_requests:
            url = req['url']
            # Убираем домен
            if self.NEW_SITE_URL in url:
                path = url.replace(self.NEW_SITE_URL, '').split('?')[0]
                if path not in api_endpoints:
                    api_endpoints[path] = {
                        'methods': set(),
                        'count': 0,
                        'full_url': url
                    }
                api_endpoints[path]['methods'].add(req['method'])
                api_endpoints[path]['count'] += 1
        
        for path, info in sorted(api_endpoints.items(), key=lambda x: -x[1]['count']):
            methods = ', '.join(info['methods'])
            logger.info(f"   {info['full_url']}")
            logger.info(f"      Methods: {methods}, Count: {info['count']}")
            
        # Сохраняем все запросы
        with open('scripts/responses/api_requests.json', 'w', encoding='utf-8') as f:
            json.dump(self.api_requests, f, ensure_ascii=False, indent=2, default=str)
        logger.info("\n💾 Все API запросы сохранены в scripts/responses/api_requests.json")
        
        # Сохраняем все ответы
        with open('scripts/responses/api_responses.json', 'w', encoding='utf-8') as f:
            json.dump(self.api_responses, f, ensure_ascii=False, indent=2, default=str)
        logger.info("💾 Все API ответы сохранены в scripts/responses/api_responses.json")
        
    async def full_scan(self):
        """Полное сканирование сайта"""
        import os
        os.makedirs('scripts/screenshots', exist_ok=True)
        os.makedirs('scripts/responses', exist_ok=True)
        
        await self.start()
        
        try:
            await self.scan_main_page()
            await self.explore_api()
            await self.test_search()
            
            # Генерируем отчет
            await self._generate_report()
            
        finally:
            await self.stop()
            
    async def _generate_report(self):
        """Генерация отчета"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 ГЕНЕРАЦИЯ ОТЧЕТА")
        logger.info("=" * 60)
        
        report = {
            'scan_date': datetime.now().isoformat(),
            'site_url': self.NEW_SITE_URL,
            'total_requests': len(self.api_requests),
            'total_responses': len(self.api_responses),
            'api_endpoints': [],
            'page_structure': {},
            'cities': {}
        }
        
        # Анализируем endpoints
        endpoints = {}
        for req in self.api_requests:
            url = req['url']
            if self.NEW_SITE_URL in url:
                path = url.replace(self.NEW_SITE_URL, '').split('?')[0]
                if path and path not in endpoints:
                    endpoints[path] = {
                        'url': req['url'],
                        'method': req['method'],
                        'headers': req['headers'],
                        'post_data': req['post_data']
                    }
        
        report['api_endpoints'] = list(endpoints.values())
        
        with open('scripts/responses/scan_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        logger.info("💾 Отчет сохранен в scripts/responses/scan_report.json")


async def main():
    scanner = SiteScanner(headless=False)
    await scanner.full_scan()
    logger.info("\n✅ Сканирование завершено!")


if __name__ == '__main__':
    asyncio.run(main())
