#!/usr/bin/env python3
"""
Изолированная система мониторинга маршрутов
Критически важный модуль с максимальной защитой от ошибок
Реализует best practices для asyncio и error handling
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta, time as datetime_time
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# Создаем отдельный logger для мониторинга
monitoring_logger = logging.getLogger("RouteMonitoring")
monitoring_logger.setLevel(logging.INFO)

# Файловый handler для критических ошибок мониторинга
monitoring_log_dir = Path('data/logs')
monitoring_log_dir.mkdir(parents=True, exist_ok=True)
monitoring_file_handler = logging.FileHandler(
    monitoring_log_dir / 'route_monitoring.log',
    encoding='utf-8'
)
monitoring_file_handler.setLevel(logging.WARNING)
monitoring_file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
monitoring_logger.addHandler(monitoring_file_handler)


class RouteMonitoringError(Exception):
    """Базовое исключение для ошибок мониторинга"""
    pass


class RouteMonitoringValidator:
    """Валидатор данных мониторинга с расширенными проверками"""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Валидация конфигурации мониторинга
        
        Returns:
            (is_valid, error_message)
        """
        required_fields = ['date', 'direction', 'time_type', 'time_range', 'chat_id']
        
        for field in required_fields:
            if field not in config:
                return False, f"Отсутствует обязательное поле: {field}"
        
        # Валидация направления
        valid_directions = [
            'minsk_ostrovets',
            'ostrovets_minsk',
            'minsk_smorgon',
            'smorgon_minsk',
            'ostrovets_smorgon',
            'smorgon_ostrovets',
            'all',
        ]
        if config['direction'] not in valid_directions:
            return False, f"Недопустимое направление: {config['direction']}"
        
        # Валидация типа времени
        valid_time_types = ['departure', 'arrival', 'any']
        if config['time_type'] not in valid_time_types:
            return False, f"Недопустимый тип времени: {config['time_type']}"
        
        # Валидация chat_id
        if not isinstance(config['chat_id'], int):
            return False, f"chat_id должен быть числом: {config['chat_id']}"
        
        # Валидация даты
        try:
            datetime.strptime(config['date'], '%Y-%m-%d')
        except ValueError:
            return False, f"Недопустимый формат даты: {config['date']} (дата должна быть YYYY-MM-DD)"
        
        return True, None
    
    @staticmethod
    def validate_routes_data(routes_data: Any) -> tuple[bool, Optional[str]]:
        """Валидация данных маршрутов"""
        if not isinstance(routes_data, dict):
            return False, "Данные маршрутов должны быть словарем"
        
        if not routes_data.get('success', False):
            return False, "Не удалось получить данные маршрутов"
        
        return True, None
    
    @staticmethod
    def should_monitoring_stop(config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Проверяет, должен ли мониторинг остановиться
        
        Args:
            config: Конфигурация мониторинга
            
        Returns:
            (should_stop, reason)
        """
        try:
            current_time = datetime.now()
            monitoring_date = datetime.strptime(config['date'], '%Y-%m-%d').date()
            current_date = current_time.date()
            
            # Если дата мониторинга прошла
            if monitoring_date < current_date:
                return True, f"Дата мониторинга ({monitoring_date}) уже прошла"
            
            # Если это день мониторинга, проверяем диапазон времени
            if monitoring_date == current_date:
                time_range = config.get('time_range', 'any')
                
                # Если диапазон времени не "любое"
                if time_range not in ['any', 'любое время']:
                    try:
                        # Парсим диапазон времени
                        if '-' in time_range:
                            end_time_str = time_range.split('-')[1].strip()
                            end_hour, end_minute = map(int, end_time_str.split(':'))
                            end_time = datetime_time(end_hour, end_minute)
                            current_time_only = current_time.time()
                            
                            # Проверяем, прошло ли время окончания диапазона
                            # Добавляем буфер в 30 минут после окончания
                            buffer_minutes = 30
                            end_datetime = datetime.combine(current_date, end_time)
                            end_with_buffer = end_datetime + timedelta(minutes=buffer_minutes)
                            
                            if current_time >= end_with_buffer:
                                return True, (
                                    f"Время мониторинга ({time_range}) завершено. "
                                    f"Текущее время: {current_time.strftime('%H:%M')}"
                                )
                    except (ValueError, IndexError) as e:
                        monitoring_logger.warning(
                            f"Ошибка парсинга времени для проверки остановки: {e}"
                        )
            
            return False, None
            
        except Exception as e:
            monitoring_logger.error(
                f"Ошибка проверки необходимости остановки мониторинга: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            return False, None


class RouteMonitoringSystem:
    """Изолированная система мониторинга маршрутов"""
    
    def __init__(self):
        """Инициализация системы мониторинга"""
        self.logger = monitoring_logger
        self.validator = RouteMonitoringValidator()
        self.parser = None
        self.bot = None
        
        self.logger.info("🚀 RouteMonitoringSystem инициализирована")
    
    def set_parser(self, parser):
        """Устанавливает парсер для получения данных маршрутов"""
        self.parser = parser
        self.logger.info("✅ Парсер установлен")
    
    def set_bot(self, bot):
        """Устанавливает бот для отправки уведомлений"""
        self.bot = bot
        self.logger.info("✅ Бот установлен")
    
    async def check_routes_for_user(
        self,
        user_id: int,
        config: Dict[str, Any],
        active_monitors: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Проверка рейсов для конкретного пользователя с автоматической остановкой
        
        Args:
            user_id: ID пользователя
            config: Конфигурация мониторинга
            active_monitors: Словарь активных мониторингов
            
        Returns:
            Результат проверки с детальной информацией
        """
        result = {
            'success': False,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'routes_found': 0,
            'error': None,
            'warnings': [],
            'should_stop': False,
            'stop_reason': None
        }
        
        try:
            self.logger.info(f"🔍 [{user_id}] Начало проверки маршрутов")
            
            # Проверяем, что мониторинг все еще активен
            if user_id not in active_monitors:
                result['warnings'].append("Мониторинг был остановлен")
                result['should_stop'] = True
                result['stop_reason'] = "monitoring_not_active"
                self.logger.warning(f"⚠️ [{user_id}] Мониторинг не найден в active_monitors")
                return result
            
            # Проверяем, нужно ли остановить мониторинг по времени
            should_stop, stop_reason = self.validator.should_monitoring_stop(config)
            if should_stop:
                result['should_stop'] = True
                result['stop_reason'] = stop_reason
                self.logger.info(
                    f"⏰ [{user_id}] Автоматическая остановка мониторинга: {stop_reason}"
                )
                
                # Отправляем уведомление об остановке
                await self.send_monitoring_stopped_notification(
                    user_id=user_id,
                    config=config,
                    reason=stop_reason
                )
                
                return result
            
            # Валидация конфигурации
            is_valid, error_msg = self.validator.validate_config(config)
            if not is_valid:
                result['error'] = f"Недопустимая конфигурация: {error_msg}"
                self.logger.error(f"❌ [{user_id}] Валидация конфигурации не прошла: {error_msg}")
                raise RouteMonitoringError(result['error'])
            
            # Проверяем наличие парсера
            if not self.parser:
                result['error'] = "Парсер не инициализирован"
                self.logger.error(f"❌ [{user_id}] Парсер отсутствует")
                raise RouteMonitoringError(result['error'])
            
            # Получаем данные маршрутов с таймаутом
            self.logger.info(f"📡 [{user_id}] Запрос данных маршрутов на {config['date']}")
            try:
                routes_data = await asyncio.wait_for(
                    self.parser.get_all_routes(config['date']),
                    timeout=30.0  # 30 секунд таймаут
                )
            except asyncio.TimeoutError:
                result['error'] = "Таймаут получения данных маршрутов"
                result['warnings'].append("Превышено время ожидания ответа от сервера")
                self.logger.error(f"⏰ [{user_id}] Таймаут получения маршрутов")
                return result
            
            # Валидация полученных данных
            is_valid, error_msg = self.validator.validate_routes_data(routes_data)
            if not is_valid:
                result['error'] = error_msg
                result['warnings'].append("Не удалось получить данные маршрутов")
                self.logger.warning(f"⚠️ [{user_id}] {error_msg}")
                return result
            
            # Фильтруем рейсы по критериям
            self.logger.info(f"🔎 [{user_id}] Фильтрация маршрутов по критериям")
            suitable_routes = self.filter_routes_by_criteria(routes_data, config, user_id)
            
            result['routes_found'] = len(suitable_routes)
            self.logger.info(f"✅ [{user_id}] Найдено подходящих рейсов: {len(suitable_routes)}")
            
            # Отправляем уведомление если найдены подходящие рейсы
            if suitable_routes:
                self.logger.info(f"📤 [{user_id}] Отправка уведомления о {len(suitable_routes)} рейсах")
                notification_result = await self.send_monitoring_notification(
                    user_id=user_id,
                    routes=suitable_routes,
                    config=config
                )
                
                if not notification_result['success']:
                    result['warnings'].append(f"Ошибка отправки уведомления: {notification_result.get('error')}")
                    self.logger.error(f"❌ [{user_id}] Не удалось отправить уведомление: {notification_result.get('error')}")
                else:
                    self.logger.info(f"✅ [{user_id}] Уведомление отправлено успешно")
            
            result['success'] = True
            
        except RouteMonitoringError as e:
            # Ожидаемые ошибки мониторинга
            result['error'] = str(e)
            self.logger.error(f"❌ [{user_id}] Ошибка мониторинга: {e}")
            
        except asyncio.CancelledError:
            # Задача была отменена
            result['error'] = "Задача мониторинга была отменена"
            self.logger.warning(f"🚫 [{user_id}] Мониторинг отменен")
            raise  # Важно: пробрасываем CancelledError дальше
            
        except Exception as e:
            # Неожиданные ошибки
            result['error'] = f"Неожиданная ошибка: {str(e)}"
            result['traceback'] = traceback.format_exc()
            self.logger.critical(
                f"🔥 [{user_id}] КРИТИЧЕСКАЯ ОШИБКА мониторинга:\n"
                f"Error: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
        
        finally:
            self.logger.info(
                f"📊 [{user_id}] Проверка завершена. "
                f"Success: {result['success']}, Routes: {result['routes_found']}, "
                f"Warnings: {len(result['warnings'])}, Should Stop: {result['should_stop']}"
            )
        
        return result
    
    async def send_monitoring_stopped_notification(
        self,
        user_id: int,
        config: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """Отправка уведомления об автоматической остановке мониторинга
        
        Args:
            user_id: ID пользователя
            config: Конфигурация мониторинга
            reason: Причина остановки
            
        Returns:
            Результат отправки уведомления
        """
        result = {
            'success': False,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'error': None
        }
        
        try:
            self.logger.info(f"🛑 [{user_id}] Отправка уведомления об остановке мониторинга")
            
            # Проверяем наличие бота
            if not self.bot:
                result['error'] = "Бот не инициализирован"
                self.logger.error(f"❌ [{user_id}] Бот отсутствует")
                raise RouteMonitoringError(result['error'])
            
            chat_id = config['chat_id']
            
            # Формируем текст сообщения
            direction_text = self._get_direction_text(config['direction'])
            
            message_parts = [
                "⏰ **МОНИТОРИНГ АВТОМАТИЧЕСКИ ОСТАНОВЛЕН**",
                "",
                f"📅 **Дата:** {config['date']}",
                f"🛣️ **Направление:** {direction_text}",
                f"⏰ **Время:** {config['time_range']}",
                "",
                f"📌 **Причина:** {reason}",
                "",
                "💡 Вы можете настроить новый мониторинг через /start"
            ]
            
            message = "\n".join(message_parts)
            
            # Создаем клавиатуру
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 Настроить новый мониторинг", callback_data="setup_monitoring")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ])
            
            # Отправляем сообщение
            self.logger.info(f"📤 [{user_id}] Отправка уведомления об остановке в chat {chat_id}")
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            result['success'] = True
            self.logger.info(f"✅ [{user_id}] Уведомление об остановке успешно отправлено")
            
        except RouteMonitoringError as e:
            result['error'] = str(e)
            self.logger.error(f"❌ [{user_id}] Ошибка отправки уведомления об остановке: {e}")
            
        except Exception as e:
            result['error'] = f"Неожиданная ошибка отправки: {str(e)}"
            self.logger.critical(
                f"🔥 [{user_id}] КРИТИЧЕСКАЯ ОШИБКА отправки уведомления об остановке:\n"
                f"Error: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
        
        return result
    
    def filter_routes_by_criteria(
        self,
        routes_data: Dict[str, Any],
        config: Dict[str, Any],
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Фильтрация рейсов по критериям пользователя
        
        Args:
            routes_data: Данные всех маршрутов
            config: Конфигурация мониторинга
            user_id: ID пользователя (для логирования)
            
        Returns:
            Список подходящих маршрутов
        """
        suitable_routes = []
        
        try:
            # Определяем, какие маршруты проверять
            routes_to_check = []
            direction = config['direction']
            if direction == 'both':
                direction = 'all'
            
            if direction in ['minsk_ostrovets', 'all']:
                minsk_to_ostrovets = routes_data.get('minsk_to_ostrovets', [])
                routes_to_check.extend(minsk_to_ostrovets)
                self.logger.debug(f"[{user_id}] Добавлено {len(minsk_to_ostrovets)} маршрутов Минск→Островец")
            
            if direction in ['ostrovets_minsk', 'all']:
                ostrovets_to_minsk = routes_data.get('ostrovets_to_minsk', [])
                routes_to_check.extend(ostrovets_to_minsk)
                self.logger.debug(f"[{user_id}] Добавлено {len(ostrovets_to_minsk)} маршрутов Островец→Минск")
            
            if direction in ['minsk_smorgon', 'all']:
                minsk_to_smorgon = routes_data.get('minsk_to_smorgon', [])
                routes_to_check.extend(minsk_to_smorgon)
                self.logger.debug(f"[{user_id}] Добавлено {len(minsk_to_smorgon)} маршрутов Минск→Сморгонь")
            
            if direction in ['smorgon_minsk', 'all']:
                smorgon_to_minsk = routes_data.get('smorgon_to_minsk', [])
                routes_to_check.extend(smorgon_to_minsk)
                self.logger.debug(f"[{user_id}] Добавлено {len(smorgon_to_minsk)} маршрутов Сморгонь→Минск")
            
            if direction in ['ostrovets_smorgon', 'all']:
                ostrovets_to_smorgon = routes_data.get('ostrovets_to_smorgon', [])
                routes_to_check.extend(ostrovets_to_smorgon)
                self.logger.debug(f"[{user_id}] Добавлено {len(ostrovets_to_smorgon)} маршрутов Островец→Сморгонь")
            
            if direction in ['smorgon_ostrovets', 'all']:
                smorgon_to_ostrovets = routes_data.get('smorgon_to_ostrovets', [])
                routes_to_check.extend(smorgon_to_ostrovets)
                self.logger.debug(f"[{user_id}] Добавлено {len(smorgon_to_ostrovets)} маршрутов Сморгонь→Островец")
            
            self.logger.info(f"[{user_id}] Всего маршрутов для проверки: {len(routes_to_check)}")
            
            # Фильтруем каждый маршрут
            for route in routes_to_check:
                try:
                    # Проверяем наличие мест
                    seats = route.get('available_seats', 0)
                    if not isinstance(seats, int) or seats <= 0:
                        continue
                    
                    # Проверяем время, если задан диапазон
                    if config['time_range'] not in ['any', 'любое время']:
                        if not self.check_time_criteria(route, config, user_id):
                            continue
                    
                    suitable_routes.append(route)
                    self.logger.debug(
                        f"[{user_id}] ✅ Подходящий маршрут: "
                        f"{route.get('departure_time', 'N/A')} - "
                        f"{route.get('arrival_time', 'N/A')}, "
                        f"мест: {seats}"
                    )
                    
                except Exception as route_error:
                    self.logger.warning(
                        f"[{user_id}] ⚠️ Ошибка при проверке маршрута: {route_error}"
                    )
                    continue
            
        except Exception as e:
            self.logger.error(
                f"[{user_id}] ❌ Ошибка фильтрации маршрутов: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
        
        return suitable_routes
    
    def check_time_criteria(
        self,
        route: Dict[str, Any],
        config: Dict[str, Any],
        user_id: int
    ) -> bool:
        """Проверка соответствия времени критериям
        
        Args:
            route: Данные маршрута
            config: Конфигурация мониторинга
            user_id: ID пользователя (для логирования)
            
        Returns:
            True если время подходит, False иначе
        """
        try:
            time_range = config['time_range']
            time_type = config['time_type']
            
            # Получаем нужное время из рейса
            if time_type == 'departure':
                route_time = route.get('departure_time', '')
            elif time_type == 'arrival':
                route_time = route.get('arrival_time', '')
            else:
                return True  # Любое время
            
            if not route_time:
                self.logger.debug(f"[{user_id}] Время маршрута отсутствует")
                return False
            
            # Парсим время рейса
            route_hour, route_minute = map(int, route_time.split(':'))
            route_minutes = route_hour * 60 + route_minute
            
            # Парсим диапазон
            if '-' in time_range:
                start_str, end_str = time_range.split('-')
                start_hour, start_minute = map(int, start_str.strip().split(':'))
                end_hour, end_minute = map(int, end_str.strip().split(':'))
                
                start_minutes = start_hour * 60 + start_minute
                end_minutes = end_hour * 60 + end_minute
                
                # Обработка диапазона через полночь
                if end_minutes < start_minutes:
                    result = route_minutes >= start_minutes or route_minutes <= end_minutes
                else:
                    result = start_minutes <= route_minutes <= end_minutes
                
                self.logger.debug(
                    f"[{user_id}] Проверка времени: {route_time} в диапазоне {time_range} = {result}"
                )
                return result
            
            return True
            
        except ValueError as e:
            self.logger.warning(
                f"[{user_id}] ⚠️ Ошибка парсинга времени: {e}. "
                f"Route time: {route.get('departure_time')}, "
                f"Range: {config.get('time_range')}"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"[{user_id}] ❌ Неожиданная ошибка проверки времени: {e}"
            )
            return True
    
    async def send_monitoring_notification(
        self,
        user_id: int,
        routes: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Отправка уведомления о найденных рейсах
        
        Args:
            user_id: ID пользователя
            routes: Список найденных маршрутов
            config: Конфигурация мониторинга
            
        Returns:
            Результат отправки уведомления
        """
        result = {
            'success': False,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'error': None
        }
        
        try:
            self.logger.info(f"📨 [{user_id}] Подготовка уведомления о {len(routes)} рейсах")
            
            # Проверяем наличие бота
            if not self.bot:
                result['error'] = "Бот не инициализирован"
                self.logger.error(f"❌ [{user_id}] Бот отсутствует")
                raise RouteMonitoringError(result['error'])
            
            chat_id = config['chat_id']
            
            # Формируем текст сообщения
            direction_text = self._get_direction_text(config['direction'])
            
            message_parts = [
                "🔔 **НАЙДЕНЫ ПОДХОДЯЩИЕ РЕЙСЫ!**",
                "",
                f"📅 **Дата:** {config['date']}",
                f"🛣️ **Направление:** {direction_text}",
                f"⏰ **Время:** {config['time_range']}",
                ""
            ]
            
            # Добавляем информацию о рейсах (максимум 5)
            for i, route in enumerate(routes[:5], 1):
                route_info = self._format_route_info(route, i)
                message_parts.append(route_info)
            
            if len(routes) > 5:
                message_parts.append(f"\n➕ И еще {len(routes) - 5} рейсов")
            
            message_parts.extend([
                "",
                "📡 Мониторинг продолжается..."
            ])
            
            message = "\n".join(message_parts)
            
            # Создаем клавиатуру
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Остановить мониторинг", callback_data="stop_monitoring")],
                [InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors")]
            ])
            
            # Отправляем сообщение
            self.logger.info(f"📤 [{user_id}] Отправка уведомления в chat {chat_id}")
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            result['success'] = True
            self.logger.info(f"✅ [{user_id}] Уведомление успешно отправлено")
            
        except RouteMonitoringError as e:
            result['error'] = str(e)
            self.logger.error(f"❌ [{user_id}] Ошибка отправки уведомления: {e}")
            
        except Exception as e:
            result['error'] = f"Неожиданная ошибка отправки: {str(e)}"
            self.logger.critical(
                f"🔥 [{user_id}] КРИТИЧЕСКАЯ ОШИБКА отправки уведомления:\n"
                f"Error: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
        
        return result
    
    def _get_direction_text(self, direction: str) -> str:
        """Получить текстовое представление направления"""
        direction_map = {
            "minsk_ostrovets": "Минск → Островец",
            "ostrovets_minsk": "Островец → Минск",
            "minsk_smorgon": "Минск → Сморгонь",
            "smorgon_minsk": "Сморгонь → Минск",
            "ostrovets_smorgon": "Островец → Сморгонь",
            "smorgon_остrovets": "Сморгонь → Островец",
            "all": "во всех направлениях",
        }
        return direction_map.get(direction, direction)
    
    def _format_route_info(self, route: Dict[str, Any], index: int) -> str:
        """Форматирование информации о рейсе"""
        try:
            departure = route.get('departure_time', 'N/A')
            arrival = route.get('arrival_time', 'N/A')
            seats = route.get('available_seats', 0)
            from_city = route.get('from_city', 'Минск')
            to_city = route.get('to_city', 'Островец')
            direction_label = f"{from_city} → {to_city}"
            emoji = "🔥" if isinstance(seats, int) and seats <= 3 else "✅"
            
            lines = [
                f"**{index}. {direction_label}**",
                f"🚀 {departure} → 🎯 {arrival}",
                f"{emoji} **{seats} мест**",
                ""
            ]
            return "\n".join(lines)
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка форматирования рейса: {e}")
            return f"\n🚌 **Рейс {index}:** Ошибка отображения"


# Создаем глобальный экземпляр системы мониторинга
route_monitoring_system = RouteMonitoringSystem()


# Экспортируемые функции для обратной совместимости
async def check_routes_for_user_job(context):
    """Обертка для job queue - проверка маршрутов для пользователя с автоматической остановкой
    
    Args:
        context: Контекст job из telegram.ext
    """
    user_id = context.job.data
    
    try:
        # Импортируем необходимые данные из bot.py
        # Используем relative import для избежания циклических зависимостей
        import sys
        from pathlib import Path
        
        # Добавляем путь к src если еще не добавлен
        src_path = str(Path(__file__).parent.parent)
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        # Импортируем нужные модули
        try:
            from bot import active_monitors, application, parser, init_parser, job_queue
        except ImportError:
            # Попытка импорта для разных окружений
            try:
                from ..bot import active_monitors, application, parser, init_parser, job_queue
            except ImportError:
                import bot as bot_module
                active_monitors = bot_module.active_monitors
                application = bot_module.application
                parser = bot_module.parser
                init_parser = bot_module.init_parser
                job_queue = bot_module.job_queue
        
        if user_id not in active_monitors:
            monitoring_logger.warning(f"⚠️ [{user_id}] Мониторинг не найден в active_monitors")
            return
        
        config = active_monitors[user_id]
        
        # Инициализируем парсер если еще не инициализирован
        if not route_monitoring_system.parser or parser is None:
            monitoring_logger.info(f"📡 [{user_id}] Инициализация парсера")
            await init_parser()
            route_monitoring_system.set_parser(parser)
        
        # Устанавливаем бот если еще не установлен
        if not route_monitoring_system.bot:
            route_monitoring_system.set_bot(application.bot)
        
        # Выполняем проверку
        result = await route_monitoring_system.check_routes_for_user(
            user_id=user_id,
            config=config,
            active_monitors=active_monitors
        )
        
        # Проверяем, нужно ли остановить мониторинг
        if result.get('should_stop', False):
            monitoring_logger.info(
                f"🛑 [{user_id}] Автоматическая остановка мониторинга. "
                f"Причина: {result.get('stop_reason')}"
            )
            
            # Удаляем мониторинг из активных
            if user_id in active_monitors:
                del active_monitors[user_id]
                monitoring_logger.info(f"✅ [{user_id}] Мониторинг удален из active_monitors")
            
            # Удаляем задачу из планировщика
            if job_queue:
                try:
                    current_jobs = job_queue.get_jobs_by_name(f"monitor_{user_id}")
                    for job in current_jobs:
                        job.schedule_removal()
                        monitoring_logger.info(f"✅ [{user_id}] Задача мониторинга удалена из job_queue")
                except Exception as job_error:
                    monitoring_logger.error(
                        f"❌ [{user_id}] Ошибка удаления задачи: {job_error}"
                    )
            
            return
        
        # Логируем результат
        if result['success']:
            if result['routes_found'] > 0:
                monitoring_logger.info(
                    f"✅ [{user_id}] Проверка выполнена успешно. "
                    f"Найдено рейсов: {result['routes_found']}"
                )
            else:
                monitoring_logger.debug(f"📭 [{user_id}] Подходящих рейсов не найдено")
        else:
            monitoring_logger.error(
                f"❌ [{user_id}] Проверка завершилась с ошибкой: {result.get('error')}"
            )
            
            # Если есть предупреждения, логируем их
            if result.get('warnings'):
                for warning in result['warnings']:
                    monitoring_logger.warning(f"⚠️ [{user_id}] {warning}")
        
    except asyncio.CancelledError:
        monitoring_logger.info(f"🚫 [{user_id}] Задача мониторинга была отменена")
        raise  # Важно: пробрасываем CancelledError дальше
        
    except Exception as e:
        monitoring_logger.critical(
            f"🔥 [{user_id}] КРИТИЧЕСКАЯ ОШИБКА в job wrapper:\n"
            f"Error: {e}\n"
            f"Traceback: {traceback.format_exc()}"
        )


__all__ = [
    'RouteMonitoringSystem',
    'RouteMonitoringError',
    'RouteMonitoringValidator',
    'route_monitoring_system',
    'check_routes_for_user_job',
    'monitoring_logger'
]
