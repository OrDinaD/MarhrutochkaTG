"""
Модули авторизации для маршруточки
"""

from .improved_web_auth import ImprovedWebAuth, UserProfile, UserBooking, RouteInfo, BookingRequest
from .requests_auth import RequestsAuthManager
from .bot_auth_manager import BotAuthManager, bot_auth_manager, format_profile_message, format_bookings_message, format_routes_message, format_booking_confirmation

__all__ = [
    'ImprovedWebAuth',
    'UserProfile', 
    'UserBooking',
    'RouteInfo',
    'BookingRequest',
    'RequestsAuthManager',
    'BotAuthManager',
    'bot_auth_manager',
    'format_profile_message',
    'format_bookings_message',
    'format_routes_message',
    'format_booking_confirmation'
]
