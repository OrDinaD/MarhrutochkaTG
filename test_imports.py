#!/usr/bin/env python3
"""Тестирование импортов модулей автопокупки"""

print("Тестирование импортов...")

try:
    from src.managers.account_manager import AccountManager
    print("✅ AccountManager импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта AccountManager: {e}")

try:
    from src.utils.ticket_buyer import TicketBuyer, AuthenticationError, BookingError
    print("✅ TicketBuyer импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта TicketBuyer: {e}")

try:
    from src.autobuy_handlers import get_account_handlers, get_autobuy_handlers
    print("✅ autobuy_handlers импортированы")
except Exception as e:
    print(f"❌ Ошибка импорта autobuy_handlers: {e}")

print("\n✅ Все импорты успешны!")
