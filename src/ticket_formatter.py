#!/usr/bin/env python3
"""
Модуль для красивого отображения билетов и информации о поездках
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class TicketFormatter:
    """Класс для форматирования билетов и информации о поездках"""
    
    @staticmethod
    def format_ticket(ticket_data: Dict) -> str:
        """
        Форматирование билета для красивого отображения
        
        Args:
            ticket_data: Данные о билете
            
        Returns:
            str: Отформатированный билет
        """
        if not ticket_data:
            return "❌ Нет данных о билете"
        
        # Базовый шаблон билета
        ticket_template = """
🎫 **БИЛЕТ НА АВТОБУС**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 **Маршрут:** {route}
📅 **Дата:** {date}
🕐 **Время:** {time}
🚌 **Рейс:** {trip_number}
💺 **Место:** {seat}
💰 **Цена:** {price}

📋 **Детали поездки:**
• Отправление: {departure}
• Прибытие: {arrival}
• Статус: {status}

🎟️ **Номер брони:** {booking_number}
📱 **Контакт:** {contact}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Приезжайте на остановку за 10 минут до отправления
🆔 Билет действителен только на указанную дату и время
        """
        
        try:
            # Извлекаем данные из ticket_data или устанавливаем значения по умолчанию
            formatted_ticket = ticket_template.format(
                route=ticket_data.get('route', 'Не указан'),
                date=ticket_data.get('date', datetime.now().strftime('%d.%m.%Y')),
                time=ticket_data.get('time', 'Не указано'),
                trip_number=ticket_data.get('trip_number', 'Не указан'),
                seat=ticket_data.get('seat', 'Не указано'),
                price=ticket_data.get('price', 'Не указана'),
                departure=ticket_data.get('departure', 'Не указано'),
                arrival=ticket_data.get('arrival', 'Не указано'),
                status=TicketFormatter._format_status(ticket_data.get('status', 'Неизвестно')),
                booking_number=ticket_data.get('booking_number', 'Не указан'),
                contact=ticket_data.get('contact', 'Не указан')
            )
            
            return formatted_ticket.strip()
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании билета: {e}")
            return f"❌ Ошибка форматирования билета: {str(e)}"
    
    @staticmethod
    def format_booking_list(bookings: List[Dict]) -> str:
        """
        Форматирование списка бронирований
        
        Args:
            bookings: Список бронирований
            
        Returns:
            str: Отформатированный список
        """
        if not bookings:
            return "📋 У вас пока нет активных бронирований"
        
        header = "📋 **ВАШИ БРОНИРОВАНИЯ**\n" + "═" * 40 + "\n\n"
        
        formatted_bookings = []
        for i, booking in enumerate(bookings, 1):
            booking_text = f"""
🎫 **Бронирование #{i}**
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Маршрут: {booking.get('route', 'Не указан')}
📅 Дата: {booking.get('date', 'Не указана')}
🕐 Время: {booking.get('time', 'Не указано')}
💰 Цена: {booking.get('price', 'Не указана')}
📊 Статус: {TicketFormatter._format_status(booking.get('status', 'Неизвестно'))}
🎟️ № брони: {booking.get('booking_number', 'Не указан')}
"""
            formatted_bookings.append(booking_text.strip())
        
        footer = f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📊 Всего бронирований: {len(bookings)}"
        
        return header + "\n\n".join(formatted_bookings) + footer
    
    @staticmethod
    def format_route_search_results(routes: List[Dict]) -> str:
        """
        Форматирование результатов поиска маршрутов
        
        Args:
            routes: Список найденных маршрутов
            
        Returns:
            str: Отформатированные результаты
        """
        if not routes:
            return "🔍 По вашему запросу маршруты не найдены"
        
        header = f"🚌 **НАЙДЕННЫЕ МАРШРУТЫ** ({len(routes)} шт.)\n" + "═" * 50 + "\n"
        
        formatted_routes = []
        for i, route in enumerate(routes, 1):
            route_text = f"""
🚌 **Рейс #{i}**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 **Маршрут:** {route.get('route', 'Не указан')}
🕐 **Отправление:** {route.get('departure_time', 'Не указано')}
🏁 **Прибытие:** {route.get('arrival_time', 'Не указано')}
⏱️ **В пути:** {route.get('duration', 'Не указано')}
💰 **Цена:** {route.get('price', 'Не указана')}
💺 **Свободных мест:** {route.get('available_seats', 'Не указано')}
🚌 **Транспорт:** {route.get('vehicle_type', 'Автобус')}
"""
            
            # Добавляем дополнительную информацию если есть
            if route.get('stops'):
                route_text += f"🛑 **Остановки:** {', '.join(route['stops'])}\n"
            
            if route.get('carrier'):
                route_text += f"🏢 **Перевозчик:** {route['carrier']}\n"
            
            formatted_routes.append(route_text.strip())
        
        footer = f"\n{'='*50}\n💡 Для бронирования выберите подходящий рейс"
        
        return header + "\n\n".join(formatted_routes) + footer
    
    @staticmethod
    def format_profile_info(profile: Dict) -> str:
        """
        Форматирование информации профиля
        
        Args:
            profile: Данные профиля
            
        Returns:
            str: Отформатированная информация профиля
        """
        if profile.get('error'):
            return f"❌ Ошибка получения профиля: {profile['error']}"
        
        profile_template = """
👤 **МОЙ ПРОФИЛЬ**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 **Личная информация:**
• Имя: {name}
• Телефон: {phone}
• Email: {email}

💰 **Финансы:**
• Баланс: {balance}

🔗 **Система:**
• Профиль: {url}
• Обновлено: {timestamp}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        try:
            # Форматируем время
            timestamp = profile.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_time = timestamp
            else:
                formatted_time = datetime.now().strftime('%d.%m.%Y %H:%M')
            
            formatted_profile = profile_template.format(
                name=profile.get('name', 'Не указано'),
                phone=profile.get('phone', 'Не указан'),
                email=profile.get('email', 'Не указан'),
                balance=profile.get('balance', 'Не указан'),
                url=profile.get('url', 'Недоступен'),
                timestamp=formatted_time
            )
            
            return formatted_profile.strip()
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании профиля: {e}")
            return f"❌ Ошибка форматирования профиля: {str(e)}"
    
    @staticmethod
    def format_booking_status(status_data: Dict) -> str:
        """
        Форматирование статуса бронирования
        
        Args:
            status_data: Данные о статусе бронирования
            
        Returns:
            str: Отформатированный статус
        """
        if status_data.get('error'):
            return f"❌ Ошибка проверки статуса: {status_data['error']}"
        
        if status_data.get("status") == "error":
            return f"❌ **Ошибка проверки статуса:** {status_data.get('message', 'Неизвестная ошибка')}"
        
        if status_data.get("status") == "not_found":
            return f"❌ **Бронирование не найдено**\n\n" \
                   f"🎟️ **Номер:** {status_data.get('booking_number', 'N/A')}\n" \
                   f"📅 **Проверено:** {TicketFormatter._format_datetime_static(status_data.get('timestamp'))}\n\n" \
                   f"💡 Проверьте правильность номера бронирования"
        
        if status_data.get("status") == "demo":
            return f"📊 **СТАТУС БРОНИРОВАНИЯ** (демо)\n" \
                   f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n" \
                   f"🎟️ **Номер брони:** {status_data.get('booking_number', 'N/A')}\n" \
                   f"📍 **Маршрут:** {status_data.get('route', 'N/A')}\n" \
                   f"📅 **Дата:** {status_data.get('date', 'N/A')}\n" \
                   f"🕐 **Время:** {status_data.get('time', 'N/A')}\n" \
                   f"💰 **Цена:** {status_data.get('price', 'N/A')}\n" \
                   f"📊 **Статус:** {status_data.get('booking_status', 'N/A')}\n\n" \
                   f"📅 **Проверено:** {TicketFormatter._format_datetime_static(status_data.get('timestamp'))}\n" \
                   f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        status_template = """
📋 **СТАТУС БРОНИРОВАНИЯ**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎟️ **Номер брони:** {booking_number}
📊 **Статус:** {status}
🕐 **Проверено:** {timestamp}

📝 **Дополнительная информация:**
{content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        try:
            # Форматируем время
            timestamp = status_data.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_time = timestamp
            else:
                formatted_time = datetime.now().strftime('%d.%m.%Y %H:%M')
            
            # Обрезаем контент если он слишком длинный
            content = status_data.get('content', 'Информация недоступна')
            if len(content) > 500:
                content = content[:500] + "..."
            
            formatted_status = status_template.format(
                booking_number=status_data.get('booking_number', 'Не указан'),
                status=TicketFormatter._format_status(status_data.get('status', 'Неизвестно')),
                timestamp=formatted_time,
                content=content
            )
            
            return formatted_status.strip()
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании статуса: {e}")
            return f"❌ Ошибка форматирования статуса: {str(e)}"
    
    @staticmethod
    def _format_status(status: str) -> str:
        """
        Форматирование статуса с эмодзи
        
        Args:
            status: Текстовый статус
            
        Returns:
            str: Статус с эмодзи
        """
        status_lower = status.lower()
        
        status_map = {
            'подтвержден': '✅ Подтвержден',
            'confirmed': '✅ Подтвержден',
            'активен': '🟢 Активен',
            'active': '🟢 Активен',
            'ожидание': '🟡 Ожидание подтверждения',
            'pending': '🟡 Ожидание подтверждения',
            'отменен': '❌ Отменен',
            'cancelled': '❌ Отменен',
            'canceled': '❌ Отменен',
            'завершен': '🏁 Завершен',
            'completed': '🏁 Завершен',
            'expired': '⏰ Истек',
            'истек': '⏰ Истек'
        }
        
        for key, formatted in status_map.items():
            if key in status_lower:
                return formatted
        
        return f"❓ {status}"
    
    @staticmethod
    def format_error_message(error: str) -> str:
        """
        Форматирование сообщения об ошибке
        
        Args:
            error: Текст ошибки
            
        Returns:
            str: Отформатированная ошибка
        """
        return f"""
❌ **ПРОИЗОШЛА ОШИБКА**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 {error}

🔧 **Что можно сделать:**
• Попробуйте позже
• Проверьте введенные данные
• Обратитесь в поддержку

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """.strip()
    
    @staticmethod
    def format_success_message(message: str) -> str:
        """
        Форматирование сообщения об успехе
        
        Args:
            message: Текст сообщения
            
        Returns:
            str: Отформатированное сообщение
        """
        return f"""
✅ **ОПЕРАЦИЯ ВЫПОЛНЕНА УСПЕШНО**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 {message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """.strip()
    
    @staticmethod
    def _format_datetime_static(timestamp: str) -> str:
        """
        Статический метод для форматирования даты-времени
        
        Args:
            timestamp: Временная метка в ISO формате
            
        Returns:
            str: Отформатированная дата-время
        """
        if not timestamp:
            return datetime.now().strftime('%d.%m.%Y %H:%M')
        
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%d.%m.%Y %H:%M')
        except:
            return timestamp
