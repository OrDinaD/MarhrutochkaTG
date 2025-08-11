#!/usr/bin/env python3
"""
Адаптер для интеграции улучшенной системы авторизации в телеграм бот
"""

import logging
import os
import json
from typing import Dict, Optional, Any

try:
    from .improved_web_auth import ImprovedWebAuth, UserProfile, UserBooking
except ImportError:
    from improved_web_auth import ImprovedWebAuth, UserProfile, UserBooking

logger = logging.getLogger(__name__)


class BotAuthManager:
    """Менеджер авторизации для телеграм бота"""
    
    def __init__(self):
        self.sessions: Dict[int, ImprovedWebAuth] = {}
        self.sessions_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "user_sessions")
        os.makedirs(self.sessions_dir, exist_ok=True)
    
    def _get_session_file(self, user_id: int) -> str:
        """Возвращает путь к файлу сессии пользователя"""
        return os.path.join(self.sessions_dir, f"user_{user_id}_session.json")
    
    def is_authenticated(self, user_id: int) -> bool:
        """Проверяет, авторизован ли пользователь"""
        if user_id in self.sessions:
            return self.sessions[user_id].authenticated
        
        # Пытаемся загрузить сессию из файла
        return self.load_session(user_id)
    
    def login(self, user_id: int, phone: str, password: str) -> bool:
        """
        Авторизация пользователя
        
        Args:
            user_id: Telegram ID пользователя
            phone: Номер телефона
            password: Пароль
            
        Returns:
            bool: True если авторизация успешна
        """
        try:
            logger.info(f"Авторизация пользователя {user_id}")
            
            # Создаем новый объект авторизации
            auth = ImprovedWebAuth()
            
            # Пытаемся авторизоваться
            success = auth.login(phone, password)
            
            if success:
                # Сохраняем сессию
                self.sessions[user_id] = auth
                self.save_session(user_id)
                logger.info(f"Пользователь {user_id} авторизован успешно")
                return True
            else:
                logger.warning(f"Не удалось авторизовать пользователя {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка авторизации пользователя {user_id}: {e}")
            return False
    
    def logout(self, user_id: int) -> bool:
        """Выход пользователя из системы"""
        try:
            if user_id in self.sessions:
                # Выполняем выход через веб-интерфейс
                self.sessions[user_id].logout()
                del self.sessions[user_id]
            
            # Удаляем файл сессии
            session_file = self._get_session_file(user_id)
            if os.path.exists(session_file):
                os.remove(session_file)
            
            logger.info(f"Пользователь {user_id} вышел из системы")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при выходе пользователя {user_id}: {e}")
            return False
    
    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Получает профиль пользователя"""
        if not self.is_authenticated(user_id):
            return None
            
        try:
            auth = self.sessions[user_id]
            profile = auth.get_user_profile()
            return profile
        except Exception as e:
            logger.error(f"Ошибка получения профиля пользователя {user_id}: {e}")
            return None
    
    def get_user_bookings(self, user_id: int, booking_type: str = "upcoming") -> list:
        """Получает бронирования пользователя"""
        if not self.is_authenticated(user_id):
            return []
            
        try:
            auth = self.sessions[user_id]
            bookings = auth.get_user_bookings(booking_type)
            return bookings
        except Exception as e:
            logger.error(f"Ошибка получения бронирований пользователя {user_id}: {e}")
            return []
    
    def search_routes(self, user_id: int, from_location: str, to_location: str, date: str):
        """Поиск маршрутов для пользователя"""
        if not self.is_authenticated(user_id):
            logger.warning(f"Пользователь {user_id} не авторизован для поиска маршрутов")
            return []
            
        try:
            auth = self.sessions[user_id]
            routes = auth.search_routes(from_location, to_location, date)
            logger.info(f"Найдено {len(routes)} маршрутов для пользователя {user_id}")
            return routes
            
        except Exception as e:
            logger.error(f"Ошибка поиска маршрутов для пользователя {user_id}: {e}")
            return []
    
    def book_ticket(self, user_id: int, booking_request) -> Optional:
        """Бронирование билета для пользователя"""
        if not self.is_authenticated(user_id):
            logger.warning(f"Пользователь {user_id} не авторизован для бронирования")
            return None
            
        try:
            auth = self.sessions[user_id]
            booking = auth.book_ticket(booking_request)
            
            if booking:
                logger.info(f"Билет забронирован для пользователя {user_id}: {booking.booking_id}")
            
            return booking
            
        except Exception as e:
            logger.error(f"Ошибка бронирования для пользователя {user_id}: {e}")
            return None
    
    def save_session(self, user_id: int) -> bool:
        """Сохраняет сессию пользователя"""
        if user_id not in self.sessions:
            return False
            
        try:
            session_file = self._get_session_file(user_id)
            auth = self.sessions[user_id]
            return auth.save_session(session_file)
        except Exception as e:
            logger.error(f"Ошибка сохранения сессии пользователя {user_id}: {e}")
            return False
    
    def load_session(self, user_id: int) -> bool:
        """Загружает сессию пользователя"""
        try:
            session_file = self._get_session_file(user_id)
            if not os.path.exists(session_file):
                return False
            
            # Создаем новый объект авторизации
            auth = ImprovedWebAuth()
            
            # Загружаем сессию
            success = auth.load_session(session_file)
            
            if success:
                self.sessions[user_id] = auth
                logger.info(f"Сессия пользователя {user_id} загружена")
                return True
            else:
                logger.info(f"Сессия пользователя {user_id} недействительна")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка загрузки сессии пользователя {user_id}: {e}")
            return False
    
    def get_auth_object(self, user_id: int) -> Optional[ImprovedWebAuth]:
        """Возвращает объект авторизации для пользователя"""
        if self.is_authenticated(user_id):
            return self.sessions.get(user_id)
        return None


# Глобальный экземпляр менеджера
bot_auth_manager = BotAuthManager()


def format_profile_message(profile: UserProfile) -> str:
    """Форматирует информацию о профиле для отображения в боте"""
    if not profile:
        return "❌ **Не удалось загрузить профиль**"
    
    message_parts = [
        "👤 **ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ**",
        ""
    ]
    
    # Формируем полное ФИО в правильном порядке
    name_parts = []
    if profile.surname:  # Фамилия
        name_parts.append(profile.surname)
    if profile.name:     # Имя  
        name_parts.append(profile.name)
    if profile.patronymic:  # Отчество
        name_parts.append(profile.patronymic)
    
    if name_parts:
        full_name = " ".join(name_parts)
        message_parts.append(f"📝 **ФИО:** {full_name}")
    
    if profile.email:
        message_parts.append(f"📧 **Email:** {profile.email}")
    
    if profile.phone:
        message_parts.append(f"📱 **Телефон:** {profile.phone}")
    
    if profile.birth_date:
        # Форматируем дату рождения
        try:
            from datetime import datetime
            if '-' in profile.birth_date:
                # Если дата в формате YYYY-MM-DD, переводим в DD.MM.YYYY
                date_obj = datetime.strptime(profile.birth_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d.%m.%Y')
                message_parts.append(f"🎂 **Дата рождения:** {formatted_date}")
            else:
                message_parts.append(f"🎂 **Дата рождения:** {profile.birth_date}")
        except:
            message_parts.append(f"🎂 **Дата рождения:** {profile.birth_date}")
    
    if profile.passport_series:
        message_parts.append(f"🆔 **Серия паспорта:** {profile.passport_series}")
    
    if profile.card_number:
        message_parts.append(f"💳 **Номер карточки:** {profile.card_number}")
    
    return "\n".join(message_parts)


def format_bookings_message(bookings: list, booking_type: str = "upcoming") -> str:
    """Форматирует информацию о бронированиях для отображения в боте"""
    type_names = {
        "upcoming": "ПРЕДСТОЯЩИЕ ПОЕЗДКИ",
        "completed": "ВЫПОЛНЕННЫЕ ПОЕЗДКИ", 
        "cancelled": "ОТМЕНЕННЫЕ ПОЕЗДКИ"
    }
    
    message_parts = [
        f"🎫 **{type_names.get(booking_type, 'ПОЕЗДКИ').upper()}**",
        ""
    ]
    
    if not bookings:
        message_parts.append("❌ Поездки не найдены")
        return "\n".join(message_parts)


def format_routes_message(routes: list, from_location: str, to_location: str, date: str) -> str:
    """Форматирует список маршрутов для отображения в боте"""
    if not routes:
        return f"❌ **Маршруты не найдены**\n\n📅 {date}\n🗺️ {from_location} → {to_location}"
    
    message_parts = [
        f"🚌 **НАЙДЕННЫЕ МАРШРУТЫ**",
        f"📅 **Дата:** {date}",
        f"🗺️ **Маршрут:** {from_location} → {to_location}",
        ""
    ]
    
    for i, route in enumerate(routes[:5], 1):  # Показываем первые 5
        route_info = [
            f"**{i}. {route.departure_time}**"
        ]
        
        if route.price:
            route_info.append(f"💰 {route.price} руб.")
        
        if route.available_seats > 0:
            route_info.append(f"🪑 {route.available_seats} мест")
        else:
            route_info.append("🚫 Мест нет")
        
        if route.bus_info:
            route_info.append(f"🚐 {route.bus_info}")
        
        if route.duration:
            route_info.append(f"⏱️ {route.duration}")
        
        message_parts.append(" • ".join(route_info))
    
    if len(routes) > 5:
        message_parts.append(f"\n... и еще {len(routes) - 5} маршрутов")
    
    return "\n".join(message_parts)


def format_booking_confirmation(booking, route_info=None) -> str:
    """Форматирует подтверждение бронирования"""
    if not booking:
        return "❌ **Ошибка бронирования**\n\nНе удалось создать бронирование."
    
    message_parts = [
        "✅ **БИЛЕТ ЗАБРОНИРОВАН!**",
        "",
        f"🎫 **Номер брони:** {booking.booking_id}",
    ]
    
    if booking.ticket_number:
        message_parts.append(f"🎟️ **Номер билета:** {booking.ticket_number}")
    
    if booking.date:
        message_parts.append(f"📅 **Дата:** {booking.date}")
    
    if booking.departure_time:
        message_parts.append(f"🕒 **Время отправления:** {booking.departure_time}")
    
    if booking.price:
        message_parts.append(f"💰 **Стоимость:** {booking.price}")
    
    if route_info:
        message_parts.extend([
            "",
            "📍 **Детали маршрута:**",
            f"   🗺️ {route_info.get('from_location', '')} → {route_info.get('to_location', '')}",
        ])
    
    message_parts.extend([
        "",
        "ℹ️ **Важно:**",
        "• Сохраните номер брони",
        "• Приезжайте на остановку за 10 минут",
        "• При посадке предъявите документ"
    ])
    
    return "\n".join(message_parts)
    
    for i, booking in enumerate(bookings[:10], 1):  # Показываем первые 10
        status_emoji = {
            'confirmed': '✅',
            'active': '🟢', 
            'cancelled': '❌',
            'expired': '⏰',
            'paid': '💰'
        }.get(booking.status, '❓')
        
        message_parts.append(
            f"**{i}. Бронирование #{booking.booking_id}**\n"
            f"   🛣️ {booking.route}\n"
            f"   📅 {booking.date} в {booking.departure_time}\n"
            f"   🎫 Билет: {booking.ticket_number}\n"
            f"   💰 Цена: {booking.price}\n"
            f"   {status_emoji} Статус: {booking.status}\n"
        )
    
    if len(bookings) > 10:
        message_parts.append(f"... и еще {len(bookings) - 10} поездок")
    
    return "\n".join(message_parts)
