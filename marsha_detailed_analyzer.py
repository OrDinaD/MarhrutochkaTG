#!/usr/bin/env python3
"""
Детальный анализ сайта маршруточки для понимания его структуры и возможностей
"""

import asyncio
from playwright.async_api import async_playwright

class MarshaDetailedAnalyzer:
    def __init__(self):
        self.base_url = "https://билет.маршруточка.бел"
        self.login = "+375299605390"
        self.password = "Zxcvbnm,1"
        
    async def run(self):
        """Основной метод анализа"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=1000)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                print("🔍 Начинаем детальный анализ сайта маршруточки...")
                
                # 1. Анализ главной страницы
                await self.analyze_main_page(page)
                
                # 2. Анализ процесса авторизации
                await self.analyze_login_process(page)
                
                # 3. Поиск всех доступных страниц
                await self.discover_pages(page)
                
                # 4. Анализ функционала без авторизации
                await self.analyze_guest_functionality(page)
                
                print("✅ Детальный анализ завершен!")
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                await page.screenshot(path="analyzer_error.png", full_page=True)
                
            finally:
                print("🔍 Оставляю браузер открытым для просмотра...")
                input("Нажмите Enter для закрытия...")
                await browser.close()
    
    async def analyze_main_page(self, page):
        """Детальный анализ главной страницы"""
        print("\n📱 АНАЛИЗ ГЛАВНОЙ СТРАНИЦЫ")
        print("=" * 50)
        
        await page.goto(self.base_url, wait_until='networkidle')
        
        # Основная информация
        title = await page.title()
        url = page.url
        print(f"📄 Заголовок: {title}")
        print(f"🌐 URL: {url}")
        
        # Анализ структуры
        html_content = await page.content()
        print(f"📏 Размер HTML: {len(html_content)} символов")
        
        # Анализ элементов
        elements_stats = await self.get_elements_stats(page)
        print("\n📊 Статистика элементов:")
        for element_type, count in elements_stats.items():
            print(f"   {element_type}: {count}")
        
        # Анализ форм
        await self.analyze_forms(page)
        
        # Анализ ссылок
        await self.analyze_links(page)
        
        # Скриншот
        await page.screenshot(path="detailed_main_page.png", full_page=True)
        print("📸 Скриншот главной страницы сохранен")
    
    async def get_elements_stats(self, page):
        """Получение статистики элементов"""
        stats = {}
        
        element_types = [
            ('Ссылки', 'a'),
            ('Формы', 'form'),
            ('Кнопки', 'button'),
            ('Поля ввода', 'input'),
            ('Изображения', 'img'),
            ('Скрипты', 'script'),
            ('Стили', 'style, link[rel="stylesheet"]'),
            ('Div контейнеры', 'div'),
            ('Списки', 'ul, ol'),
            ('Таблицы', 'table')
        ]
        
        for name, selector in element_types:
            try:
                elements = await page.query_selector_all(selector)
                stats[name] = len(elements)
            except:
                stats[name] = 0
        
        return stats
    
    async def analyze_forms(self, page):
        """Анализ форм на странице"""
        print("\n📝 АНАЛИЗ ФОРМ")
        print("-" * 30)
        
        forms = await page.query_selector_all('form')
        print(f"Найдено форм: {len(forms)}")
        
        for i, form in enumerate(forms, 1):
            print(f"\n🔹 Форма #{i}:")
            try:
                # Атрибуты формы
                action = await form.get_attribute('action')
                method = await form.get_attribute('method')
                form_class = await form.get_attribute('class')
                form_id = await form.get_attribute('id')
                
                print(f"   Action: {action}")
                print(f"   Method: {method}")
                print(f"   Class: {form_class}")
                print(f"   ID: {form_id}")
                
                # Поля формы
                inputs = await form.query_selector_all('input')
                print(f"   Полей ввода: {len(inputs)}")
                
                for j, input_field in enumerate(inputs, 1):
                    input_type = await input_field.get_attribute('type')
                    input_name = await input_field.get_attribute('name')
                    input_placeholder = await input_field.get_attribute('placeholder')
                    input_id = await input_field.get_attribute('id')
                    
                    print(f"      Поле {j}: type='{input_type}', name='{input_name}', placeholder='{input_placeholder}', id='{input_id}'")
                
                # Кнопки формы
                buttons = await form.query_selector_all('button')
                for j, button in enumerate(buttons, 1):
                    button_type = await button.get_attribute('type')
                    button_text = await button.text_content()
                    print(f"      Кнопка {j}: type='{button_type}', text='{button_text}'")
                    
            except Exception as e:
                print(f"   Ошибка анализа формы: {e}")
    
    async def analyze_links(self, page):
        """Анализ ссылок на странице"""
        print("\n🔗 АНАЛИЗ ССЫЛОК")
        print("-" * 30)
        
        links = await page.query_selector_all('a')
        print(f"Найдено ссылок: {len(links)}")
        
        unique_links = set()
        categories = {
            'Внутренние': [],
            'Внешние': [],
            'Якорные': [],
            'JavaScript': [],
            'Телефоны': [],
            'Email': []
        }
        
        for link in links:
            try:
                href = await link.get_attribute('href')
                text = await link.text_content()
                
                if not href:
                    continue
                
                href = href.strip()
                text = text.strip() if text else ''
                
                if href in unique_links:
                    continue
                unique_links.add(href)
                
                link_info = f"{text} -> {href}"
                
                if href.startswith('tel:'):
                    categories['Телефоны'].append(link_info)
                elif href.startswith('mailto:'):
                    categories['Email'].append(link_info)
                elif href.startswith('#'):
                    categories['Якорные'].append(link_info)
                elif href.startswith('javascript:'):
                    categories['JavaScript'].append(link_info)
                elif href.startswith('http') and 'маршруточка' not in href:
                    categories['Внешние'].append(link_info)
                else:
                    categories['Внутренние'].append(link_info)
                    
            except Exception as e:
                continue
        
        for category, links_list in categories.items():
            if links_list:
                print(f"\n📌 {category} ссылки ({len(links_list)}):")
                for link in links_list[:5]:  # Показываем первые 5
                    print(f"   {link}")
                if len(links_list) > 5:
                    print(f"   ... и еще {len(links_list) - 5}")
    
    async def analyze_login_process(self, page):
        """Детальный анализ процесса авторизации"""
        print("\n🔐 АНАЛИЗ ПРОЦЕССА АВТОРИЗАЦИИ")
        print("=" * 50)
        
        # Сначала ищем элементы входа на главной странице
        await page.goto(self.base_url, wait_until='networkidle')
        
        # Ищем кнопку входа
        login_selectors = [
            'text="Войти"',
            '[class*="login"]',
            '[id*="login"]',
            'a:has-text("Войти")',
            'button:has-text("Войти")'
        ]
        
        login_element = None
        for selector in login_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=2000)
                if element:
                    print(f"✅ Найден элемент входа: {selector}")
                    login_element = element
                    break
            except:
                continue
        
        if not login_element:
            print("❌ Элемент входа не найден")
            return
        
        # Кликаем по элементу входа
        print("🖱️ Кликаем по элементу входа...")
        await login_element.click()
        await page.wait_for_timeout(2000)
        
        # Анализируем изменения на странице
        await self.analyze_login_form(page)
        
        # Скриншот после клика
        await page.screenshot(path="after_login_click.png", full_page=True)
        print("📸 Скриншот после клика на вход сохранен")
    
    async def analyze_login_form(self, page):
        """Анализ формы авторизации"""
        print("\n📋 АНАЛИЗ ФОРМЫ АВТОРИЗАЦИИ")
        print("-" * 40)
        
        # Ищем все видимые поля ввода
        input_fields = await page.query_selector_all('input')
        visible_inputs = []
        
        for input_field in input_fields:
            try:
                is_visible = await input_field.is_visible()
                if is_visible:
                    input_type = await input_field.get_attribute('type')
                    input_name = await input_field.get_attribute('name')
                    input_placeholder = await input_field.get_attribute('placeholder')
                    input_id = await input_field.get_attribute('id')
                    input_class = await input_field.get_attribute('class')
                    
                    field_info = {
                        'type': input_type,
                        'name': input_name,
                        'placeholder': input_placeholder,
                        'id': input_id,
                        'class': input_class,
                        'element': input_field
                    }
                    visible_inputs.append(field_info)
                    
            except:
                continue
        
        print(f"Найдено видимых полей ввода: {len(visible_inputs)}")
        
        for i, field in enumerate(visible_inputs, 1):
            print(f"   Поле {i}:")
            print(f"      Type: {field['type']}")
            print(f"      Name: {field['name']}")
            print(f"      Placeholder: {field['placeholder']}")
            print(f"      ID: {field['id']}")
            print(f"      Class: {field['class']}")
        
        # Пробуем заполнить форму
        await self.attempt_login_fill(page, visible_inputs)
    
    async def attempt_login_fill(self, page, visible_inputs):
        """Попытка заполнить форму авторизации"""
        print("\n🔑 ПОПЫТКА ЗАПОЛНЕНИЯ ФОРМЫ")
        print("-" * 40)
        
        # Ищем поле для телефона
        phone_field = None
        for field in visible_inputs:
            if (field['type'] in ['tel', 'text'] and 
                (field['name'] and 'phone' in field['name'].lower()) or
                (field['placeholder'] and 'телефон' in field['placeholder'].lower()) or
                (field['id'] and 'phone' in field['id'].lower())):
                phone_field = field['element']
                print(f"✅ Найдено поле для телефона: {field}")
                break
        
        # Ищем поле для пароля
        password_field = None
        for field in visible_inputs:
            if field['type'] == 'password':
                password_field = field['element']
                print(f"✅ Найдено поле для пароля: {field}")
                break
        
        # Заполняем поля
        try:
            if phone_field:
                await phone_field.fill(self.login)
                print("✅ Телефон заполнен")
            else:
                print("❌ Поле телефона не найдено")
            
            if password_field:
                await password_field.fill(self.password)
                print("✅ Пароль заполнен")
            else:
                print("❌ Поле пароля не найдено")
            
            if phone_field and password_field:
                # Скриншот заполненной формы
                await page.screenshot(path="filled_login_form.png", full_page=True)
                print("📸 Скриншот заполненной формы сохранен")
                
                # Ищем кнопку отправки
                await self.find_and_click_submit(page)
                
        except Exception as e:
            print(f"❌ Ошибка при заполнении формы: {e}")
    
    async def find_and_click_submit(self, page):
        """Поиск и нажатие кнопки отправки"""
        print("\n🚀 ПОИСК И НАЖАТИЕ КНОПКИ ОТПРАВКИ")
        print("-" * 40)
        
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Войти")',
            'button:has-text("Вход")',
            'button:has-text("Отправить")'
        ]
        
        for selector in submit_selectors:
            try:
                button = await page.wait_for_selector(selector, timeout=2000)
                if button and await button.is_visible():
                    print(f"✅ Найдена кнопка отправки: {selector}")
                    await button.click()
                    print("🚀 Кнопка нажата")
                    
                    # Ждем загрузки
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # Анализируем результат
                    await self.analyze_login_result(page)
                    return
                    
            except:
                continue
        
        print("❌ Кнопка отправки не найдена")
    
    async def analyze_login_result(self, page):
        """Анализ результата авторизации"""
        print("\n📊 АНАЛИЗ РЕЗУЛЬТАТА АВТОРИЗАЦИИ")
        print("-" * 40)
        
        current_url = page.url
        title = await page.title()
        
        print(f"🌐 URL после авторизации: {current_url}")
        print(f"📄 Заголовок после авторизации: {title}")
        
        # Проверяем наличие элементов, указывающих на успешную авторизацию
        success_indicators = [
            'text="Выйти"',
            'text="Профиль"',
            'text="Мой профиль"',
            '[class*="user"]',
            '[class*="profile"]'
        ]
        
        authenticated = False
        for indicator in success_indicators:
            try:
                element = await page.query_selector(indicator)
                if element:
                    print(f"✅ Найден индикатор авторизации: {indicator}")
                    authenticated = True
                    break
            except:
                continue
        
        if not authenticated:
            print("❌ Индикаторы успешной авторизации не найдены")
        
        # Скриншот результата
        await page.screenshot(path="login_result.png", full_page=True)
        print("📸 Скриншот результата авторизации сохранен")
        
        return authenticated
    
    async def discover_pages(self, page):
        """Обнаружение доступных страниц"""
        print("\n🗺️ ОБНАРУЖЕНИЕ ДОСТУПНЫХ СТРАНИЦ")
        print("=" * 50)
        
        # Список потенциальных страниц для проверки
        potential_pages = [
            '/profile',
            '/user',
            '/account',
            '/my-account',
            '/dashboard',
            '/bookings',
            '/tickets',
            '/my-tickets',
            '/trips',
            '/my-trips',
            '/history',
            '/orders',
            '/settings',
            '/logout'
        ]
        
        base_domain = self.base_url.replace('https://', '').replace('http://', '')
        
        for page_path in potential_pages:
            test_url = f"https://{base_domain}{page_path}"
            
            try:
                response = await page.goto(test_url, wait_until='networkidle', timeout=5000)
                status = response.status if response else 0
                title = await page.title()
                
                if status == 200 and "404" not in title:
                    print(f"✅ Доступная страница: {test_url} (Статус: {status}, Заголовок: {title})")
                else:
                    print(f"❌ Недоступная страница: {test_url} (Статус: {status})")
                    
            except Exception as e:
                print(f"❌ Ошибка при проверке {test_url}: {str(e)[:50]}...")
            
            # Небольшая пауза между запросами
            await page.wait_for_timeout(500)
    
    async def analyze_guest_functionality(self, page):
        """Анализ функционала для гостей"""
        print("\n👥 АНАЛИЗ ФУНКЦИОНАЛА ДЛЯ ГОСТЕЙ")
        print("=" * 50)
        
        # Возвращаемся на главную
        await page.goto(self.base_url, wait_until='networkidle')
        
        # Анализируем поисковую форму
        await self.analyze_search_form(page)
        
        # Анализируем статус бронирования
        await self.analyze_booking_status(page)
    
    async def analyze_search_form(self, page):
        """Анализ поисковой формы"""
        print("\n🔍 АНАЛИЗ ПОИСКОВОЙ ФОРМЫ")
        print("-" * 40)
        
        # Ищем поля поиска
        search_fields = {
            'Откуда': ['input[placeholder*="Откуда"]', 'input[name*="from"]'],
            'Куда': ['input[placeholder*="Куда"]', 'input[name*="to"]'],
            'Дата': ['input[type="date"]', 'input[placeholder*="дата"]']
        }
        
        found_fields = {}
        for field_name, selectors in search_fields.items():
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        found_fields[field_name] = selector
                        print(f"✅ Найдено поле '{field_name}': {selector}")
                        break
                except:
                    continue
        
        # Тестируем поиск
        if len(found_fields) >= 2:
            print("🧪 Тестируем поиск маршрутов...")
            await self.test_route_search(page, found_fields)
        else:
            print("❌ Недостаточно полей для тестирования поиска")
    
    async def test_route_search(self, page, found_fields):
        """Тестирование поиска маршрутов"""
        try:
            if 'Откуда' in found_fields:
                from_field = await page.query_selector(found_fields['Откуда'])
                await from_field.fill('Минск')
                print("✅ Заполнено поле 'Откуда': Минск")
            
            if 'Куда' in found_fields:
                to_field = await page.query_selector(found_fields['Куда'])
                await to_field.fill('Гродно')
                print("✅ Заполнено поле 'Куда': Гродно")
            
            # Ищем кнопку поиска
            search_button = await page.query_selector('button:has-text("Найти"), input[type="submit"]')
            if search_button:
                await page.screenshot(path="before_search.png", full_page=True)
                print("📸 Скриншот перед поиском сохранен")
                
                # Не нажимаем кнопку, чтобы не перейти на другую страницу
                print("🔍 Форма поиска готова к отправке")
            else:
                print("❌ Кнопка поиска не найдена")
                
        except Exception as e:
            print(f"❌ Ошибка при тестировании поиска: {e}")
    
    async def analyze_booking_status(self, page):
        """Анализ функции проверки статуса бронирования"""
        print("\n📋 АНАЛИЗ ПРОВЕРКИ СТАТУСА БРОНИРОВАНИЯ")
        print("-" * 40)
        
        # Ищем элементы для проверки статуса
        status_selectors = [
            'text="Статус бронирования"',
            '[class*="status"]',
            '[id*="status"]',
            'input[placeholder*="номер"]',
            'input[placeholder*="код"]'
        ]
        
        for selector in status_selectors:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    print(f"✅ Найден элемент статуса: {selector}")
            except:
                continue

async def main():
    analyzer = MarshaDetailedAnalyzer()
    await analyzer.run()

if __name__ == "__main__":
    print("🔬 Запуск детального анализатора сайта маршруточки...")
    asyncio.run(main())
