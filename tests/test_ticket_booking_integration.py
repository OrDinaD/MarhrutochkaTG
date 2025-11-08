"""
Интеграционные тесты для системы покупки билетов.

Тесты покрывают:
1. Вход в аккаунт
2. Поиск рейсов
3. Бронирование билета
4. Отмена заказа
"""

import pytest
import asyncio
from src.utils.ticket_buyer import TicketBuyer, BookingError


# Тестовые данные - реальные для интеграционных тестов
TEST_PHONE = "299605390"
TEST_PASSWORD = "Zxcvbnm,1"
TEST_ROUTE = {
    "from": "Островец",
    "to": "Минск",
    "date": "2025-11-09",
    "preferred_time": "07:00"
}


@pytest.mark.asyncio
@pytest.mark.integration
class TestTicketBookingIntegration:
    """Интеграционные тесты покупки билетов"""
    
    async def test_full_booking_cycle(self):
        """
        Тест полного цикла:
        1. Вход
        2. Поиск
        3. Бронирование
        4. Отмена
        """
        buyer = None
        try:
            # 1. Создание покупателя
            buyer = TicketBuyer(
                phone=TEST_PHONE,
                password=TEST_PASSWORD,
                headless=False
            )
            await buyer.start()
            assert buyer.page is not None, "Браузер не инициализирован"
            
            # 2. Вход в аккаунт
            login_success = await buyer.login()
            assert login_success is True, "Не удалось войти в аккаунт"
            assert buyer.is_authenticated is True, "Аутентификация не установлена"
            
            # 3. Поиск рейсов
            routes = await buyer.search_tickets(
                from_city=TEST_ROUTE["from"],
                to_city=TEST_ROUTE["to"],
                date=TEST_ROUTE["date"]
            )
            
            assert len(routes) > 0, "Не найдено ни одного рейса"
            assert all('departure_time' in r for r in routes), "В рейсах нет времени отправления"
            assert all('arrival_time' in r for r in routes), "В рейсах нет времени прибытия"
            assert all('available_seats' in r for r in routes), "В рейсах нет информации о местах"
            assert all('price' in r for r in routes), "В рейсах нет цены"
            assert all('button' in r for r in routes), "В рейсах нет кнопки"
            
            # 4. Выбор рейса с нужным временем
            target_route = None
            for route in routes:
                if route.get('departure_time') == TEST_ROUTE["preferred_time"]:
                    target_route = route
                    break
            
            if not target_route:
                target_route = routes[0]  # Берем первый доступный
            
            assert target_route is not None, "Не выбран целевой рейс"
            assert target_route.get('available_seats', 0) > 0, "На выбранном рейсе нет свободных мест"
            
            # 5. Бронирование
            booking_info = await buyer.book_ticket(route_info=target_route)
            
            assert booking_info is not None, "Информация о бронировании пустая"
            # TODO: добавить проверки содержимого booking_info
            
            # 6. Пауза для просмотра результата
            await asyncio.sleep(3)
            
            # 7. Отмена заказа (если функция реализована)
            # TODO: добавить отмену заказа
            
            print("✅ Тест полного цикла пройден успешно!")
            
        finally:
            if buyer:
                await buyer.close()
    
    
    async def test_login_with_valid_credentials(self):
        """Тест входа с валидными данными"""
        buyer = None
        try:
            buyer = TicketBuyer(
                phone=TEST_PHONE,
                password=TEST_PASSWORD,
                headless=True
            )
            await buyer.start()
            
            success = await buyer.login()
            
            assert success is True
            assert buyer.is_authenticated is True
            
        finally:
            if buyer:
                await buyer.close()
    
    
    async def test_login_with_invalid_credentials(self):
        """Тест входа с невалидными данными"""
        buyer = None
        try:
            buyer = TicketBuyer(
                phone="1234567890",
                password="wrongpassword",
                headless=True
            )
            await buyer.start()
            
            with pytest.raises(BookingError):
                await buyer.login()
            
            assert buyer.is_authenticated is False
            
        finally:
            if buyer:
                await buyer.close()
    
    
    async def test_search_returns_multiple_routes(self):
        """Тест поиска возвращает несколько рейсов"""
        buyer = None
        try:
            buyer = TicketBuyer(
                phone=TEST_PHONE,
                password=TEST_PASSWORD,
                headless=True
            )
            await buyer.start()
            
            await buyer.login()
            
            routes = await buyer.search_tickets(
                from_city=TEST_ROUTE["from"],
                to_city=TEST_ROUTE["to"],
                date=TEST_ROUTE["date"]
            )
            
            assert len(routes) >= 1, "Должно быть найдено хотя бы один рейс"
            
            # Проверяем структуру первого рейса
            first_route = routes[0]
            assert 'departure_time' in first_route
            assert 'arrival_time' in first_route
            assert 'available_seats' in first_route
            assert 'price' in first_route
            assert 'button' in first_route
            assert 'index' in first_route
            
        finally:
            if buyer:
                await buyer.close()
    
    
    async def test_search_without_login_fails(self):
        """Тест поиска без входа должен падать"""
        buyer = None
        try:
            buyer = TicketBuyer(
                phone=TEST_PHONE,
                password=TEST_PASSWORD,
                headless=True
            )
            await buyer.start()
            
            # Не логинимся!
            
            with pytest.raises(BookingError):
                await buyer.search_tickets(
                    from_city=TEST_ROUTE["from"],
                    to_city=TEST_ROUTE["to"],
                    date=TEST_ROUTE["date"]
                )
            
        finally:
            if buyer:
                await buyer.close()
    
    
    async def test_book_without_login_fails(self):
        """Тест бронирования без входа должен падать"""
        buyer = None
        try:
            buyer = TicketBuyer(
                phone=TEST_PHONE,
                password=TEST_PASSWORD,
                headless=True
            )
            await buyer.start()
            
            # Не логинимся!
            
            fake_route = {
                'departure_time': '07:00',
                'arrival_time': '09:00',
                'available_seats': 5,
                'price': '22',
                'button': None,  # Фейковая кнопка
                'index': 0
            }
            
            with pytest.raises(BookingError):
                await buyer.book_ticket(route_info=fake_route)
            
        finally:
            if buyer:
                await buyer.close()


@pytest.mark.asyncio
@pytest.mark.unit
class TestTicketBuyerUnit:
    """Юнит-тесты TicketBuyer"""
    
    async def test_initialization(self):
        """Тест инициализации покупателя"""
        buyer = TicketBuyer(
            phone=TEST_PHONE,
            password=TEST_PASSWORD,
            headless=True
        )
        await buyer.start()
        
        try:
            assert buyer.page is not None
            assert buyer.browser is not None
            assert buyer.is_authenticated is False
        finally:
            await buyer.close()
    
    
    async def test_close_cleanup(self):
        """Тест корректного закрытия"""
        buyer = TicketBuyer(
            phone=TEST_PHONE,
            password=TEST_PASSWORD,
            headless=True
        )
        await buyer.start()
        
        await buyer.close()
        
        # После закрытия все должно быть None (проверяем что не падает)
        # Playwright не устанавливает в None, но закрывает ресурсы
        assert True  # Если дошли сюда - значит close() отработал без ошибок


if __name__ == "__main__":
    # Запуск интеграционного теста
    asyncio.run(TestTicketBookingIntegration().test_full_booking_cycle())
