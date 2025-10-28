#!/usr/bin/env python3
"""
Модуль административной панели для бота
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pathlib import Path

logger = logging.getLogger(__name__)

LOG_FILE_PATH = Path(__file__).resolve().parent.parent / 'data' / 'logs' / 'bot.log'

class AdminPanel:
    """Административная панель для управления ботом"""
    
    def __init__(self, admin_telegram_id: int):
        self.admin_telegram_id = admin_telegram_id
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        return user_id == self.admin_telegram_id
    
    def get_admin_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру административной панели"""
        keyboard = [
            [InlineKeyboardButton("📊 Статистика мониторингов", callback_data="admin_monitoring_stats")],
            [InlineKeyboardButton("👥 Активные пользователи", callback_data="admin_active_users")],
            [InlineKeyboardButton("🔍 Поиск пользователя", callback_data="admin_search_user")],
            [InlineKeyboardButton("📋 Логи системы", callback_data="admin_system_logs")],
            [InlineKeyboardButton("⚙️ Настройки бота", callback_data="admin_bot_settings")],
            [InlineKeyboardButton("🔁 Перезагрузить бота", callback_data="admin_restart_bot")],
            [InlineKeyboardButton("🚨 Экстренные функции", callback_data="admin_emergency")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_monitoring_statistics(self, active_monitors: Dict) -> str:
        """Возвращает статистику мониторингов (без legacy user_sessions)"""
        if not active_monitors:
            return "📊 **Статистика мониторингов**\n\n❌ Активных мониторингов нет"
        
        # Общая статистика
        total_monitors = len(active_monitors)
        
        # Статистика по направлениям
        direction_stats = {}
        time_stats = {}
        date_stats = {}
        
        for user_id, config in active_monitors.items():
            direction = config.get('direction', 'unknown')
            direction_stats[direction] = direction_stats.get(direction, 0) + 1
            
            time_type = config.get('time_type', 'unknown')
            time_stats[time_type] = time_stats.get(time_type, 0) + 1
            
            date = config.get('date', 'unknown')
            date_stats[date] = date_stats.get(date, 0) + 1
        
        # Формируем отчет
        report_parts = [
            "📊 **СТАТИСТИКА МОНИТОРИНГОВ**",
            "",
            f"🔢 **Общие показатели:**",
            f"• Активных мониторингов: **{total_monitors}**",
            f"• Уникальных пользователей: **{total_monitors}**",
            "",
            "🛣️ **По направлениям:**"
        ]
        
        direction_names = {
            'minsk_ostrovets': 'Минск → Островец',
            'ostrovets_minsk': 'Островец → Минск',
            'both': 'Оба направления'
        }
        
        for direction, count in direction_stats.items():
            name = direction_names.get(direction, direction)
            report_parts.append(f"• {name}: **{count}**")
        
        report_parts.extend([
            "",
            "⏰ **По типу времени:**"
        ])
        
        time_names = {
            'departure': 'Время отправления',
            'arrival': 'Время прибытия',
            'any': 'Любое время'
        }
        
        for time_type, count in time_stats.items():
            name = time_names.get(time_type, time_type)
            report_parts.append(f"• {name}: **{count}**")
        
        # Топ-3 популярных дат
        if date_stats:
            sorted_dates = sorted(date_stats.items(), key=lambda x: x[1], reverse=True)[:3]
            report_parts.extend([
                "",
                "📅 **Популярные даты:**"
            ])
            
            for date, count in sorted_dates:
                report_parts.append(f"• {date}: **{count}** мониторингов")
        
        return "\n".join(report_parts)
    
    def get_active_users_info(self, active_monitors: Dict, user_data_store: Dict) -> str:
        """Возвращает информацию об активных пользователях"""
        all_user_ids = set()
        all_user_ids.update(active_monitors.keys())
        all_user_ids.update(user_data_store.keys())
        
        if not all_user_ids:
            return "👥 **Активные пользователи**\n\n❌ Активных пользователей нет"
        
        report_parts = [
            "👥 **АКТИВНЫЕ ПОЛЬЗОВАТЕЛИ**",
            "",
            f"🔢 **Всего пользователей:** {len(all_user_ids)}",
            ""
        ]
        
        # Детальная информация по пользователям
        for i, user_id in enumerate(sorted(all_user_ids), 1):
            if i > 10:  # Показываем только первых 10
                report_parts.append(f"... и еще {len(all_user_ids) - 10} пользователей")
                break
                
            user_info = [f"**{i}. User ID:** `{user_id}`"]
            
            # Проверяем мониторинг
            if user_id in active_monitors:
                config = active_monitors[user_id]
                direction = config.get('direction', 'unknown')
                date = config.get('date', 'unknown')
                user_info.append(f"   🔔 Мониторинг: {direction} на {date}")
            
            # Legacy авторизация удалена - используется memory-only режим
            
            # Проверяем активность
            if user_id in user_data_store:
                user_info.append(f"   📱 Активные данные в памяти")
            
            report_parts.append("\n".join(user_info))
            
        return "\n".join(report_parts)
    
    def get_system_logs(self, lines: int = 20) -> str:
        """Возвращает последние системные логи"""
        try:
            if LOG_FILE_PATH.exists():
                with LOG_FILE_PATH.open('r', encoding='utf-8') as log_file:
                    all_lines = log_file.readlines()
                    last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                report_parts = [
                    "📋 **СИСТЕМНЫЕ ЛОГИ**",
                    f"(последние {len(last_lines)} строк)",
                    "",
                    "```"
                ]
                
                for line in last_lines:
                    # Ограничиваем длину строки для Telegram
                    if len(line) > 100:
                        line = line[:97] + "..."
                    report_parts.append(line.strip())
                
                report_parts.append("```")
                
                return "\n".join(report_parts)
            else:
                return "📋 **СИСТЕМНЫЕ ЛОГИ**\n\n❌ Файл логов не найден"
                
        except Exception as e:
            return f"📋 **СИСТЕМНЫЕ ЛОГИ**\n\n❌ Ошибка чтения логов: {str(e)}"
    
    def get_bot_settings(self) -> str:
        """Возвращает текущие настройки бота"""
        import os
        
        report_parts = [
            "⚙️ **НАСТРОЙКИ БОТА**",
            "",
            "🔧 **Переменные окружения:**"
        ]
        
        # Показываем основные настройки (без секретных данных)
        env_vars = [
            'MONITORING_ENABLED',
            'MONITORING_INTERVAL_MINUTES',
            'ALERT_THRESHOLD_SEATS',
            'PLAYWRIGHT_HEADLESS',
            'PLAYWRIGHT_TIMEOUT'
        ]
        
        for var in env_vars:
            value = os.getenv(var, 'не установлено')
            report_parts.append(f"• {var}: `{value}`")
        
        # Показываем статус токена (но не сам токен)
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        token_status = "установлен" if token else "не установлен"
        report_parts.append(f"• TELEGRAM_BOT_TOKEN: `{token_status}`")
        
        # Показываем статус админа
        admin_id = os.getenv('ADMIN_TELEGRAM_ID')
        admin_status = "установлен" if admin_id else "не установлен"
        report_parts.append(f"• ADMIN_TELEGRAM_ID: `{admin_status}`")
        
        return "\n".join(report_parts)
    
    def get_emergency_functions_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру экстренных функций"""
        keyboard = [
            [InlineKeyboardButton("🛑 Остановить все мониторинги", callback_data="admin_stop_all_monitoring")],
            [InlineKeyboardButton("🔄 Перезапустить планировщик", callback_data="admin_restart_scheduler")],
            [InlineKeyboardButton("🧹 Очистить кэш пользователей", callback_data="admin_clear_user_cache")],
            [InlineKeyboardButton("📤 Экспорт данных", callback_data="admin_export_data")],
            [InlineKeyboardButton("📥 Импорт данных", callback_data="admin_import_data")],
            [InlineKeyboardButton("🔙 Админ панель", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_restart_confirmation_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру подтверждения перезапуска бота"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data="admin_restart_bot_confirm"),
                InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def stop_all_monitoring(self, active_monitors: Dict, job_queue) -> str:
        """Останавливает все активные мониторинги"""
        if not active_monitors:
            return "🛑 **Остановка мониторингов**\n\nНет активных мониторингов для остановки."
        
        stopped_count = len(active_monitors)
        
        try:
            # Останавливаем все задачи планировщика
            if job_queue:
                for user_id in list(active_monitors.keys()):
                    current_jobs = job_queue.get_jobs_by_name(f"monitor_{user_id}")
                    for job in current_jobs:
                        job.schedule_removal()
            
            # Очищаем словарь мониторингов
            active_monitors.clear()
            
            # Сохраняем изменения
            try:
                # Импортируем функцию сохранения
                from .bot import save_active_monitors  # type: ignore
                save_active_monitors()  # Может вызвать ImportError при циклическом импорте
            except:
                pass
            
            return f"🛑 **Остановка мониторингов**\n\n✅ Остановлено {stopped_count} мониторингов"
            
        except Exception as e:
            return f"🛑 **Остановка мониторингов**\n\n❌ Ошибка: {str(e)}"
    
    def clear_user_cache(self, user_data_store: Dict) -> str:
        """Очищает кэш пользовательских данных"""
        try:
            data_count = len(user_data_store)
            
            user_data_store.clear()
            
            return (
                f"🧹 **Очистка кэша**\n\n"
                f"✅ Очищено:\n"
                f"• Пользовательских данных: {data_count}\n"
                f"• Режим: memory-only (без внешних сессий)"
            )
            
        except Exception as e:
            return f"🧹 **Очистка кэша**\n\n❌ Ошибка: {str(e)}"
    
    def export_data(self, active_monitors: Dict) -> Dict:
        """Экспортирует данные бота"""
        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'active_monitors': active_monitors,
                'mode': 'memory-only',
                'total_users': len(active_monitors)
            }
            
            # Сохраняем в файл
            export_filename = f"bot_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            export_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), export_filename)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return {
                'success': True,
                'filename': export_filename,
                'path': export_path,
                'data': export_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
