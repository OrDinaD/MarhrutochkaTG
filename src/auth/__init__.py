"""
Модули авторизации для маршруточки
"""

from .improved_web_auth import ImprovedWebAuth, UserProfile, UserBooking
from .requests_auth import RequestsAuthManager
from .bot_auth_manager import BotAuthManager, bot_auth_manager, format_profile_message, format_bookings_message

__all__ = [
    'ImprovedWebAuth',
    'UserProfile', 
    'UserBooking',
    'RequestsAuthManager',
    'BotAuthManager',
    'bot_auth_manager',
    'format_profile_message',
    'format_bookings_message'
]
