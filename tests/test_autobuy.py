"""
Тесты для модуля автопокупки билетов
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.utils.ticket_buyer import TicketBuyer, AuthenticationError, BookingError
from src.managers.account_manager import AccountManager


@pytest.fixture
def account_manager():
    """Фикстура для менеджера аккаунтов"""
    return AccountManager(storage_file="test_accounts.json")


@pytest.fixture
def ticket_buyer():
    """Фикстура для покупателя билетов"""
    return TicketBuyer(phone="299605390", password="test_password", headless=True)


class TestAccountManager:
    """Тесты для менеджера аккаунтов"""
    
    def test_add_account(self, account_manager):
        """Тест добавления аккаунта"""
        result = account_manager.add_account(123456, "299605390", "password123")
        assert result is True
        assert account_manager.has_account(123456) is True
    
    def test_get_account(self, account_manager):
        """Тест получения аккаунта"""
        account_manager.add_account(123456, "299605390", "password123")
        account = account_manager.get_account(123456)
        assert account is not None
        assert account['phone'] == "299605390"
        assert account['password'] == "password123"
    
    def test_remove_account(self, account_manager):
        """Тест удаления аккаунта"""
        account_manager.add_account(123456, "299605390", "password123")
        result = account_manager.remove_account(123456)
        assert result is True
        assert account_manager.has_account(123456) is False
    
    def test_has_account_nonexistent(self, account_manager):
        """Тест проверки несуществующего аккаунта"""
        assert account_manager.has_account(999999) is False
    
    def test_encryption(self, account_manager):
        """Тест шифрования данных"""
        original_data = "test_password_123"
        encrypted = account_manager._encrypt(original_data)
        decrypted = account_manager._decrypt(encrypted)
        assert decrypted == original_data
    
    def test_get_stats(self, account_manager):
        """Тест получения статистики"""
        account_manager.add_account(123456, "299605390", "password123")
        account_manager.add_account(789012, "297777777", "password456")
        
        stats = account_manager.get_stats()
        assert stats['total_accounts'] == 2
        assert stats['users_with_accounts'] == 2


class TestTicketBuyer:
    """Тесты для покупателя билетов"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, ticket_buyer):
        """Тест инициализации"""
        assert ticket_buyer.phone == "299605390"
        assert ticket_buyer.password == "test_password"
        assert ticket_buyer.headless is True
        assert ticket_buyer.is_authenticated is False
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Тест использования как контекстного менеджера"""
        with patch('src.utils.ticket_buyer.async_playwright') as mock_playwright:
            mock_playwright.return_value.start = AsyncMock()
            mock_playwright.return_value.chromium.launch = AsyncMock()
            
            async with TicketBuyer("299605390", "test_password") as buyer:
                assert buyer is not None
    
    @pytest.mark.asyncio
    async def test_check_authenticated_true(self, ticket_buyer):
        """Тест проверки авторизации - пользователь авторизован"""
        ticket_buyer.page = MagicMock()
        ticket_buyer.page.query_selector = AsyncMock(return_value=MagicMock())
        
        result = await ticket_buyer.check_authenticated()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_authenticated_false(self, ticket_buyer):
        """Тест проверки авторизации - пользователь не авторизован"""
        ticket_buyer.page = MagicMock()
        ticket_buyer.page.query_selector = AsyncMock(return_value=None)
        
        result = await ticket_buyer.check_authenticated()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_parse_search_results_empty(self, ticket_buyer):
        """Тест парсинга пустых результатов поиска"""
        ticket_buyer.page = MagicMock()
        ticket_buyer.page.query_selector_all = AsyncMock(return_value=[])
        
        routes = await ticket_buyer._parse_search_results()
        assert routes == []
    
    @pytest.mark.asyncio
    async def test_extract_booking_info(self, ticket_buyer):
        """Тест извлечения информации о бронировании"""
        # Создаем мок страницы с данными
        mock_row = MagicMock()
        mock_cell1 = MagicMock()
        mock_cell2 = MagicMock()
        mock_cell1.text_content = AsyncMock(return_value="Количество билетов:")
        mock_cell2.text_content = AsyncMock(return_value="1")
        mock_row.query_selector_all = AsyncMock(return_value=[mock_cell1, mock_cell2])
        
        ticket_buyer.page = MagicMock()
        ticket_buyer.page.query_selector_all = AsyncMock(return_value=[mock_row])
        ticket_buyer.page.query_selector = AsyncMock(return_value=None)
        
        info = await ticket_buyer._extract_booking_info()
        assert "Количество билетов:" in info


class TestTicketBuyerIntegration:
    """Интеграционные тесты (требуют настоящий браузер - пропускаем в CI)"""
    
    @pytest.mark.skip(reason="Requires browser and credentials")
    @pytest.mark.asyncio
    async def test_login_success(self):
        """Тест успешного входа"""
        # Этот тест нужно запускать вручную с реальными учетными данными
        async with TicketBuyer("299605390", "real_password") as buyer:
            result = await buyer.login()
            assert result is True
            assert buyer.is_authenticated is True
    
    @pytest.mark.skip(reason="Requires browser")
    @pytest.mark.asyncio
    async def test_search_tickets(self):
        """Тест поиска билетов"""
        async with TicketBuyer("299605390", "real_password") as buyer:
            await buyer.login()
            routes = await buyer.search_tickets(
                from_city="Минск",
                to_city="Островец",
                date="2025-11-09"
            )
            assert isinstance(routes, list)
    
    @pytest.mark.skip(reason="Requires browser and should not book real tickets")
    @pytest.mark.asyncio
    async def test_auto_buy_ticket(self):
        """Тест автопокупки билета (не запускать без необходимости!)"""
        async with TicketBuyer("299605390", "real_password") as buyer:
            result = await buyer.auto_buy_ticket(
                from_city="Минск",
                to_city="Островец",
                date="2025-11-09",
                preferred_time="07:00"
            )
            assert 'success' in result


@pytest.mark.asyncio
async def test_ticket_buyer_error_handling():
    """Тест обработки ошибок в покупателе билетов"""
    buyer = TicketBuyer("invalid", "invalid")
    
    # Тест без запуска браузера
    with pytest.raises(BookingError):
        await buyer.search_tickets("Минск", "Островец", "2025-11-09")


def test_account_manager_persistence(tmp_path):
    """Тест сохранения аккаунтов между сессиями"""
    storage_file = tmp_path / "test_accounts.json"
    
    # Создаем менеджер и добавляем аккаунт
    manager1 = AccountManager(storage_file=str(storage_file))
    manager1.add_account(123456, "299605390", "password123")
    
    # Создаем новый менеджер и проверяем загрузку
    manager2 = AccountManager(storage_file=str(storage_file))
    assert manager2.has_account(123456) is True
    
    account = manager2.get_account(123456)
    assert account['phone'] == "299605390"
    assert account['password'] == "password123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
