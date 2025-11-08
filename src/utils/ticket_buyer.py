"""
Модуль для автоматической покупки билетов на сайте маршруток.
Использует Playwright для взаимодействия с сайтом.
"""

import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class TicketBuyerError(Exception):
    """Базовое исключение для ошибок покупки билетов"""
    pass


class AuthenticationError(TicketBuyerError):
    """Ошибка аутентификации"""
    pass


class BookingError(TicketBuyerError):
    """Ошибка бронирования билета"""
    pass


class TicketBuyer:
    """Класс для автоматической покупки билетов"""

    def __init__(self, phone: str, password: str, headless: bool = True):
        """
        Инициализация покупателя билетов.
        
        Args:
            phone: Номер телефона (без кода страны, например: 299605390)
            password: Пароль
            headless: Запускать браузер в фоновом режиме
        """
        self.phone = phone
        self.password = password
        self.headless = headless
        self.base_url = "https://xn--90aiim0b.xn--80aa3agllaqi6bg.xn--90ais"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.is_authenticated = False

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        await self.close()

    async def start(self):
        """Запустить браузер"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            self.page = await self.browser.new_page()
            logger.info("Браузер запущен")
        except Exception as e:
            logger.error(f"Ошибка запуска браузера: {e}")
            raise TicketBuyerError(f"Не удалось запустить браузер: {e}")

    async def close(self):
        """Закрыть браузер"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Браузер закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии браузера: {e}")

    async def login(self) -> bool:
        """
        Войти в аккаунт.
        
        Returns:
            True если вход успешен
            
        Raises:
            AuthenticationError: Если не удалось войти
        """
        try:
            logger.info("Начинаем процесс входа в аккаунт")
            
            # Переходим на главную страницу
            await self.page.goto(self.base_url, wait_until='networkidle')
            logger.info("Загружена главная страница")

            # Ждем и нажимаем кнопку "Войти" в навигации
            try:
                # Ждем кнопку "Войти" в верхнем меню (не в форме)
                login_link = await self.page.wait_for_selector('li:has-text("Войти")', timeout=5000)
                await login_link.click()
                logger.info("Нажата кнопка 'Войти' в меню")
                await asyncio.sleep(1.5)  # Ждем появления попапа
            except PlaywrightTimeout:
                # Возможно, уже залогинены
                if await self.check_authenticated():
                    logger.info("Уже авторизованы")
                    self.is_authenticated = True
                    return True
                raise AuthenticationError("Не найдена кнопка 'Войти'")

            # Ждем появления ВИДИМОЙ формы входа в попапе
            # Используем :visible и nth для первого видимого элемента
            await self.page.wait_for_selector('input[placeholder="Телефон"]:visible', state='visible', timeout=10000)
            logger.info("Форма входа появилась")

            # Получаем все поля телефона и находим видимое
            phone_inputs = await self.page.query_selector_all('input[placeholder="Телефон"]')
            phone_input = None
            for inp in phone_inputs:
                if await inp.is_visible():
                    phone_input = inp
                    break
            
            if phone_input:
                await phone_input.click()
                await asyncio.sleep(0.3)
                # Вводим номер БЕЗ +375 (это в combobox)
                clean_phone = self.phone.replace('+375', '').replace('+', '')
                await phone_input.fill(clean_phone)
                logger.info(f"Введен номер телефона: {clean_phone}")
            else:
                raise AuthenticationError("Не найдено поле для ввода телефона")

            # Вводим пароль - также ищем видимый элемент
            password_inputs = await self.page.query_selector_all('input[placeholder="Пароль"]')
            password_input = None
            for inp in password_inputs:
                if await inp.is_visible():
                    password_input = inp
                    break
            
            if password_input:
                await password_input.click()
                await asyncio.sleep(0.3)
                await password_input.fill(self.password)
                logger.info("Введен пароль")
            else:
                raise AuthenticationError("Не найдено поле для ввода пароля")

            # Нажимаем кнопку входа - это input[type="submit"], а не button!
            submit_buttons = await self.page.query_selector_all('input[type="submit"][value="Войти"], button:has-text("Войти")')
            submit_button = None
            for btn in submit_buttons:
                if await btn.is_visible():
                    submit_button = btn
                    break
            
            if submit_button:
                await submit_button.click()
                logger.info("Нажата кнопка входа в форме")
            else:
                raise AuthenticationError("Не найдена кнопка входа в форме")

            # Ждем завершения входа
            await asyncio.sleep(2)
            await self.page.wait_for_load_state('networkidle')

            # Проверяем успешность входа
            if await self.check_authenticated():
                logger.info("Вход в аккаунт выполнен успешно")
                self.is_authenticated = True
                return True
            else:
                raise AuthenticationError("Не удалось войти в аккаунт")

        except PlaywrightTimeout as e:
            logger.error(f"Таймаут при входе: {e}")
            raise AuthenticationError(f"Таймаут при входе: {e}")
        except Exception as e:
            logger.error(f"Ошибка при входе: {e}")
            raise AuthenticationError(f"Ошибка при входе: {e}")

    async def check_authenticated(self) -> bool:
        """
        Проверить, авторизован ли пользователь.
        
        Returns:
            True если авторизован
        """
        try:
            # Проверяем наличие элемента "Личный кабинет" или "Выйти"
            personal_cabinet = await self.page.query_selector('text=Личный кабинет')
            logout_button = await self.page.query_selector('text=Выйти')
            
            return personal_cabinet is not None or logout_button is not None
        except Exception as e:
            logger.error(f"Ошибка при проверке авторизации: {e}")
            return False

    async def search_tickets(
        self,
        from_city: str,
        to_city: str,
        date: str,
        seats: int = 1
    ) -> List[Dict]:
        """
        Найти доступные билеты.
        
        Args:
            from_city: Город отправления
            to_city: Город назначения
            date: Дата в формате YYYY-MM-DD
            seats: Количество мест
            
        Returns:
            Список доступных рейсов
        """
        try:
            logger.info(f"Поиск билетов: {from_city} -> {to_city}, дата: {date}")
            print(f"[DEBUG] Поиск билетов: {from_city} -> {to_city}, дата: {date}")
            
            # Переходим на главную страницу (важно - после входа можем быть где угодно)
            logger.info(f"Переход на главную: {self.base_url}")
            print(f"[DEBUG] Переход на главную: {self.base_url}")
            await self.page.goto(self.base_url, wait_until='networkidle')
            current_url = self.page.url
            logger.info(f"Текущий URL: {current_url}")
            print(f"[DEBUG] Текущий URL: {current_url}")
            
            # Проверяем, что мы на главной странице
            if not current_url.endswith('/') and not 'index' in current_url:
                logger.warning(f"Не на главной странице! URL: {current_url}")
                print(f"[DEBUG] Не на главной! Повторный переход...")
                await self.page.goto(self.base_url, wait_until='networkidle')
                await asyncio.sleep(1)
            
            logger.info("Загружена главная страница")
            print(f"[DEBUG] Главная страница загружена")
            
            # Делаем скриншот для отладки
            await self.page.screenshot(path='debug_main_page.png')
            print(f"[DEBUG] Скриншот сохранен: debug_main_page.png")

            # Выбираем город отправления
            logger.info(f"Выбор города отправления: {from_city}")
            print(f"[DEBUG] Ищем поле 'Откуда' (Select2)...")
            
            # Ищем Select2 элемент с текстом "Откуда" (первый на странице)
            from_city_selects = await self.page.query_selector_all('.select2-selection__rendered:has-text("Откуда")')
            if from_city_selects and len(from_city_selects) > 0:
                from_city_input = from_city_selects[0]  # Берем первый (основная форма на главной)
                print(f"[DEBUG] Select2 'Откуда' найден!")
                await from_city_input.click()
                logger.info("Клик на поле 'Откуда'")
                await asyncio.sleep(0.8)
                
                # Ищем опцию через role (более надежно)
                try:
                    from_city_option = await self.page.get_by_role('option', name=from_city).element_handle()
                    if from_city_option:
                        await from_city_option.click()
                        logger.info(f"✅ Выбран город отправления: {from_city}")
                    else:
                        raise BookingError(f"Город '{from_city}' не найден в списке")
                except Exception as e:
                    logger.error(f"Ошибка выбора города отправления: {e}")
                    raise BookingError(f"Город '{from_city}' не найден")
            else:
                raise BookingError("Не найдено поле 'Откуда'")

            # Выбираем город назначения
            await asyncio.sleep(0.8)
            logger.info(f"Выбор города назначения: {to_city}")
            print(f"[DEBUG] Ищем поле 'Куда' (Select2)...")
            
            # Ищем Select2 элемент с текстом "Куда" (первый на странице)
            to_city_selects = await self.page.query_selector_all('.select2-selection__rendered:has-text("Куда")')
            if to_city_selects and len(to_city_selects) > 0:
                to_city_input = to_city_selects[0]  # Берем первый (основная форма на главной)
                print(f"[DEBUG] Select2 'Куда' найден!")
                await to_city_input.click()
                logger.info("Клик на поле 'Куда'")
                await asyncio.sleep(0.8)
                
                try:
                    to_city_option = await self.page.get_by_role('option', name=to_city).element_handle()
                    if to_city_option:
                        await to_city_option.click()
                        logger.info(f"✅ Выбран город назначения: {to_city}")
                    else:
                        raise BookingError(f"Город '{to_city}' не найден в списке")
                except Exception as e:
                    logger.error(f"Ошибка выбора города назначения: {e}")
                    raise BookingError(f"Город '{to_city}' не найден")

            # Устанавливаем количество мест
            if seats > 1:
                logger.info(f"Установка количества мест: {seats}")
                plus_button = await self.page.query_selector('button:has-text("+")')
                for _ in range(seats - 1):
                    if plus_button:
                        await plus_button.click()
                        await asyncio.sleep(0.2)

            # Выбираем дату
            await asyncio.sleep(0.8)
            logger.info(f"Выбор даты: {date}")
            date_input = await self.page.query_selector('input[placeholder="XXXX-XX-XX"]')
            if date_input:
                await date_input.click()
                logger.info("Клик на поле даты")
                await asyncio.sleep(0.8)
                
                # Парсим дату
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                day = date_obj.day
                logger.info(f"Ищем день: {day}")
                
                # Кликаем на нужный день в календаре
                # Используем более точный селектор - td с точным текстом дня
                day_selector = f'td.day:has-text("{day}"):not(.old):not(.new)'
                day_cell = await self.page.query_selector(day_selector)
                if not day_cell:
                    # Fallback - ищем через role
                    try:
                        day_cell = await self.page.get_by_role('cell', name=str(day), exact=True).element_handle()
                    except Exception:
                        # Последняя попытка - просто любую ячейку с этим числом
                        day_cell = await self.page.query_selector(f'td:has-text("{day}")')
                
                if day_cell:
                    await day_cell.click()
                    logger.info(f"✅ Выбрана дата: {date}")
                    
                    # Ждем закрытия календаря (он закрывается автоматически)
                    await asyncio.sleep(1)
                else:
                    raise BookingError(f"День {day} не найден в календаре")

            # Нажимаем кнопку "Найти"
            await asyncio.sleep(0.3)
            search_button = await self.page.query_selector('a:has-text("Найти")')
            if search_button:
                print(f"[DEBUG] URL до клика 'Найти': {self.page.url}")
                
                # Кликаем на кнопку поиска
                await search_button.click()
                logger.info("Нажата кнопка 'Найти'")
                
                # Ждем немного
                await asyncio.sleep(2)
                print(f"[DEBUG] URL после клика 'Найти': {self.page.url}")
                
                # Ждем появления результатов (кнопок "Далее")
                # Результаты подгружаются динамически через JS
                try:
                    logger.info("Ожидание загрузки результатов...")
                    await self.page.wait_for_selector('button.seats-choice', timeout=15000)
                    logger.info("Результаты появились!")
                    await asyncio.sleep(1)  # Дополнительная пауза для полной загрузки
                    print(f"[DEBUG] Кнопок .seats-choice на странице: {len(await self.page.query_selector_all('button.seats-choice'))}")
                except Exception as e:
                    logger.warning(f"Таймаут ожидания результатов: {e}")
                    print(f"[DEBUG] Кнопок .seats-choice после таймаута: {len(await self.page.query_selector_all('button.seats-choice'))}")
                    # Продолжаем, возможно результаты уже загрузились
            else:
                logger.error("Кнопка 'Найти' не найдена!")

            # Парсим результаты
            routes = await self._parse_search_results()
            logger.info(f"Найдено рейсов: {len(routes)}")
            
            return routes

        except Exception as e:
            logger.error(f"Ошибка при поиске билетов: {e}")
            raise BookingError(f"Ошибка при поиске билетов: {e}")

    async def _parse_search_results(self) -> List[Dict]:
        """
        Парсить результаты поиска билетов.
        
        Returns:
            Список рейсов с информацией
        """
        routes = []
        
        try:
            # Ждем загрузки результатов
            await asyncio.sleep(2)
            
            # Ищем ВСЕ блоки рейсов по классу nf-route
            # Каждый рейс = это отдельный div.nf-route
            route_blocks = await self.page.query_selector_all('div.nf-route')
            
            logger.info(f"Найдено блоков рейсов: {len(route_blocks)}")
            print(f"[DEBUG] Парсер: найдено {len(route_blocks)} блоков .nf-route")
            
            import re
            
            for i, block in enumerate(route_blocks):
                try:
                    # Получаем весь текст блока
                    block_text = await block.text_content()
                    
                    print(f"[DEBUG] Рейс {i}: текст = {block_text[:200]}...")
                    
                    # Ищем кнопку "Далее" внутри этого блока
                    next_button = await block.query_selector('button.seats-choice')
                    if not next_button:
                        print(f"[DEBUG] Рейс {i}: кнопка .seats-choice не найдена, пропускаем")
                        continue
                    
                    route_info = {
                        'index': i,
                        'button': next_button
                    }
                    
                    # Парсим время (формат ЧЧ:ММ)
                    times = re.findall(r'\b(\d{1,2}:\d{2})\b', block_text)
                    if len(times) >= 2:
                        route_info['departure_time'] = times[0]
                        route_info['arrival_time'] = times[1]
                        print(f"[DEBUG] Рейс {i}: время {times[0]} → {times[1]}")
                    else:
                        print(f"[DEBUG] Рейс {i}: времена не найдены в тексте")
                    
                    # Парсим свободные места
                    seats_match = re.search(r'свободно[:\s]*(\d+)', block_text, re.IGNORECASE)
                    if seats_match:
                        route_info['available_seats'] = int(seats_match.group(1))
                        print(f"[DEBUG] Рейс {i}: свободно {seats_match.group(1)}")
                    else:
                        route_info['available_seats'] = 0
                        print(f"[DEBUG] Рейс {i}: свободные места не найдены")
                    
                    # Парсим цену
                    price_match = re.search(r'(\d+[\.,]?\d*)\s*BYN', block_text)
                    if price_match:
                        route_info['price'] = price_match.group(1)
                        print(f"[DEBUG] Рейс {i}: цена {price_match.group(1)}")
                    
                    # Парсим название компании перевозчика
                    # Обычно это последний текст перед "Заказать билет"
                    company_match = re.search(r'([А-Яа-яёЁ\s\-]+)\s*Заказать билет', block_text)
                    if company_match:
                        route_info['company'] = company_match.group(1).strip()
                    
                    if route_info.get('departure_time'):
                        routes.append(route_info)
                        logger.info(f"✅ Рейс {i}: {route_info.get('departure_time')} → {route_info.get('arrival_time')}, свободно: {route_info.get('available_seats')}, цена: {route_info.get('price')} BYN")
                    else:
                        print(f"[DEBUG] Рейс {i}: НЕ добавлен (нет времени отправления)")
                        
                except Exception as e:
                    logger.error(f"Ошибка парсинга рейса {i}: {e}")
                    print(f"[DEBUG] Ошибка на рейсе {i}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
        except Exception as e:
            logger.error(f"Ошибка парсинга результатов поиска: {e}")
            print(f"[DEBUG] Критическая ошибка парсера: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info(f"Всего найдено рейсов: {len(routes)}")
        print(f"[DEBUG] Итого в списке: {len(routes)} рейсов")
        return routes

    async def book_ticket(
        self,
        route_info: Dict,
        boarding_point: Optional[str] = None,
        alighting_point: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict:
        """
        Забронировать билет на выбранный рейс.
        
        Args:
            route_info: Словарь с информацией о рейсе (из search_tickets)
            boarding_point: Место посадки (если нужно изменить)
            alighting_point: Место высадки (если нужно изменить)
            comment: Комментарий к заказу
            
        Returns:
            Информация о бронировании
        """
        try:
            if not self.is_authenticated:
                raise BookingError("Необходимо войти в аккаунт перед бронированием")

            logger.info(f"Бронирование билета на рейс {route_info.get('departure_time')}")
            print(f"[DEBUG] Клик на кнопку 'Далее' для рейса {route_info.get('departure_time')}")

            # Получаем кнопку из route_info
            next_button = route_info.get('button')
            if not next_button:
                raise BookingError("Кнопка 'Далее' не найдена в информации о рейсе")
            
            # Кликаем на кнопку "Далее"
            await next_button.click()
            logger.info("Нажата кнопка 'Далее'")
            print("[DEBUG] Кнопка 'Далее' нажата, ждем загрузки...")
            await asyncio.sleep(2)
            
            # Делаем скриншот для отладки
            await self.page.screenshot(path='debug_after_next_button.png')
            print(f"[DEBUG] Текущий URL: {self.page.url}")
            print(f"[DEBUG] Скриншот сохранен: debug_after_next_button.png")

            # Ищем кнопку "Продолжить" или другие варианты
            # Может быть модальное окно или новая страница
            try:
                # Пробуем найти различные варианты кнопки продолжения
                continue_selectors = [
                    'button:has-text("Продолжить")',
                    'button:has-text("Далее")',
                    'button:has-text("Заказать")',
                    'button:has-text("Подтвердить")',
                    'button[type="submit"]',
                    'a:has-text("Продолжить")'
                ]
                
                continue_button = None
                for selector in continue_selectors:
                    continue_button = await self.page.query_selector(selector)
                    if continue_button:
                        button_text = await continue_button.text_content()
                        print(f"[DEBUG] Найдена кнопка: {selector} с текстом '{button_text}'")
                        break
                
                if continue_button:
                    await continue_button.click()
                    logger.info("Нажата кнопка 'Продолжить'")
                    print("[DEBUG] Кнопка 'Продолжить' нажата")
                    await asyncio.sleep(2)
                    await self.page.wait_for_load_state('networkidle')
                else:
                    # Возможно, уже на странице выбора мест
                    print("[DEBUG] Кнопка 'Продолжить' не найдена, возможно уже на странице выбора")
                    
            except Exception as e:
                print(f"[DEBUG] Ошибка поиска кнопки 'Продолжить': {e}")
                # Продолжаем, возможно уже на нужной странице

            # Теперь мы на странице оформления заказа (/order)
            
            # Изменяем место посадки, если указано
            if boarding_point:
                boarding_select = await self.page.query_selector('select, combobox')
                if boarding_select:
                    await boarding_select.select_option(label=boarding_point)
                    logger.info(f"Изменено место посадки на: {boarding_point}")

            # Изменяем место высадки, если указано
            if alighting_point:
                alighting_selects = await self.page.query_selector_all('select, combobox')
                if len(alighting_selects) > 1:
                    await alighting_selects[1].select_option(label=alighting_point)
                    logger.info(f"Изменено место высадки на: {alighting_point}")

            # Добавляем комментарий, если указан
            if comment:
                comment_input = await self.page.query_selector('textarea[placeholder="Комментарий"], input[placeholder="Комментарий"]')
                if comment_input:
                    await comment_input.fill(comment)
                    logger.info(f"Добавлен комментарий: {comment}")

            # Извлекаем информацию о бронировании
            booking_info = await self._extract_booking_info()

            # Нажимаем кнопку "Продолжить" для подтверждения заказа
            final_continue_button = await self.page.query_selector('div:has-text("Продолжить")')
            if final_continue_button:
                await final_continue_button.click()
                logger.info("Нажата кнопка подтверждения заказа")
                await asyncio.sleep(2)
                await self.page.wait_for_load_state('networkidle')

                # Проверяем успешность бронирования
                success = await self._check_booking_success()
                booking_info['success'] = success
                
                if success:
                    logger.info("Билет успешно забронирован!")
                else:
                    logger.warning("Не удалось подтвердить успешность бронирования")

            return booking_info

        except Exception as e:
            logger.error(f"Ошибка при бронировании билета: {e}")
            raise BookingError(f"Ошибка при бронировании билета: {e}")

    async def _extract_booking_info(self) -> Dict:
        """
        Извлечь информацию о бронировании со страницы заказа.
        
        Returns:
            Словарь с информацией о бронировании
        """
        info = {}
        
        try:
            # Извлекаем информацию из таблицы
            rows = await self.page.query_selector_all('table tr')
            
            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 2:
                    key_elem = cells[0]
                    value_elem = cells[1]
                    
                    key = (await key_elem.text_content()).strip()
                    value = (await value_elem.text_content()).strip()
                    
                    info[key] = value

            # Извлекаем номер места
            seat_elem = await self.page.query_selector('text=/Место №:/')
            if seat_elem:
                seat_text = await seat_elem.text_content()
                import re
                match = re.search(r'Место №:\s*(\d+)', seat_text)
                if match:
                    info['seat_number'] = match.group(1)

            # Извлекаем цену
            price_elem = await self.page.query_selector('text=/Цена:/')
            if price_elem:
                price_text = await price_elem.text_content()
                import re
                match = re.search(r'Цена:\s*([\d.]+)\s*BYN', price_text)
                if match:
                    info['price'] = match.group(1)

            logger.info(f"Извлечена информация о бронировании: {info}")
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении информации о бронировании: {e}")
        
        return info

    async def _check_booking_success(self) -> bool:
        """
        Проверить успешность бронирования.
        
        Returns:
            True если бронирование успешно
        """
        try:
            # Проверяем, перешли ли мы на страницу подтверждения
            current_url = self.page.url
            
            # Ищем признаки успешного бронирования
            success_indicators = [
                'success',
                'подтверждение',
                'заказ оформлен',
                'билет забронирован'
            ]
            
            page_content = await self.page.content()
            page_content_lower = page_content.lower()
            
            for indicator in success_indicators:
                if indicator in page_content_lower:
                    return True
            
            # Проверяем URL
            if '/success' in current_url or '/confirmation' in current_url:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке успешности бронирования: {e}")
            return False

    async def get_my_tickets(self) -> List[Dict]:
        """
        Получить список забронированных билетов.
        
        Returns:
            Список билетов пользователя
        """
        try:
            if not self.is_authenticated:
                raise BookingError("Необходимо войти в аккаунт")

            logger.info("Получение списка билетов")

            # Переходим в личный кабинет
            await self.page.goto(f"{self.base_url}/profile/tickets?upcoming", wait_until='networkidle')
            await asyncio.sleep(1)

            # Парсим билеты
            tickets = []
            
            # Ищем строки таблицы с билетами
            rows = await self.page.query_selector_all('table tbody tr')
            
            for row in rows:
                try:
                    cells = await row.query_selector_all('td')
                    
                    if len(cells) >= 6:
                        ticket_info = {
                            'number': await cells[0].text_content(),
                            'route': await cells[1].text_content(),
                            'date': await cells[2].text_content(),
                            'time': await cells[3].text_content(),
                            'ticket': await cells[4].text_content(),
                            'price': await cells[5].text_content()
                        }
                        
                        tickets.append(ticket_info)
                        
                except Exception as e:
                    logger.error(f"Ошибка парсинга билета: {e}")
                    continue

            logger.info(f"Найдено билетов: {len(tickets)}")
            return tickets

        except Exception as e:
            logger.error(f"Ошибка при получении списка билетов: {e}")
            raise BookingError(f"Ошибка при получении списка билетов: {e}")

    async def auto_buy_ticket(
        self,
        from_city: str,
        to_city: str,
        date: str,
        preferred_time: Optional[str] = None,
        min_seats: int = 1,
        max_price: Optional[float] = None
    ) -> Dict:
        """
        Автоматически найти и купить билет с заданными критериями.
        
        Args:
            from_city: Город отправления
            to_city: Город назначения
            date: Дата в формате YYYY-MM-DD
            preferred_time: Предпочитаемое время отправления (формат HH:MM)
            min_seats: Минимальное количество свободных мест
            max_price: Максимальная цена
            
        Returns:
            Информация о купленном билете
        """
        try:
            logger.info(f"Автопокупка билета: {from_city} -> {to_city}, дата: {date}")

            # Если не авторизованы, входим
            if not self.is_authenticated:
                await self.login()

            # Ищем билеты
            routes = await self.search_tickets(from_city, to_city, date, min_seats)

            logger.info(f"=== Результаты поиска ===")
            logger.info(f"Найдено рейсов всего: {len(routes)}")
            for i, route in enumerate(routes):
                logger.info(f"Рейс {i}: {route}")

            if not routes:
                raise BookingError("Не найдено доступных рейсов")

            # Фильтруем по критериям
            suitable_routes = []
            
            for route in routes:
                # Проверяем количество мест
                if route.get('available_seats', 0) < min_seats:
                    continue
                
                # Проверяем цену
                if max_price:
                    try:
                        price_str = route.get('price', '').replace('BYN', '').strip()
                        price = float(price_str)
                        if price > max_price:
                            continue
                    except (ValueError, AttributeError):
                        pass
                
                # Проверяем время
                if preferred_time:
                    departure = route.get('departure_time', '')
                    if preferred_time in departure:
                        suitable_routes.insert(0, route)  # Приоритет
                        continue
                
                suitable_routes.append(route)

            if not suitable_routes:
                raise BookingError("Не найдено рейсов, соответствующих критериям")

            # Выбираем первый подходящий рейс
            selected_route = suitable_routes[0]
            route_index = selected_route['index']

            logger.info(f"Выбран рейс: {selected_route.get('departure_time')} -> {selected_route.get('arrival_time')}")

            # Бронируем билет
            booking_info = await self.book_ticket(route_index)

            return booking_info

        except Exception as e:
            logger.error(f"Ошибка при автопокупке билета: {e}")
            raise BookingError(f"Ошибка при автопокупке билета: {e}")
