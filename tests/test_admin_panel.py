#!/usr/bin/env python3
"""
Тесты для административной панели
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from admin_panel import AdminPanel


class TestAdminPanel:
    """Тесты административной панели"""
    
    def test_admin_panel_init(self):
        """Тест инициализации админ-панели"""
        admin_id = 123456789
        panel = AdminPanel(admin_id)
        
        assert panel.admin_telegram_id == admin_id
    
    def test_is_admin_true(self):
        """Тест проверки администратора - положительный случай"""
        admin_id = 123456789
        panel = AdminPanel(admin_id)
        
        assert panel.is_admin(admin_id) is True
    
    def test_is_admin_false(self):
        """Тест проверки администратора - отрицательный случай"""
        admin_id = 123456789
        panel = AdminPanel(admin_id)
        
        assert panel.is_admin(987654321) is False
    
    def test_get_admin_menu_keyboard(self):
        """Тест генерации клавиатуры админ-панели"""
        panel = AdminPanel(123456789)
        keyboard = panel.get_admin_menu_keyboard()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
        
        # Проверяем наличие основных кнопок
        buttons_text = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "📊 Статистика мониторингов" in buttons_text
        assert "👥 Активные пользователи" in buttons_text
        assert "🔙 Главное меню" in buttons_text
    
    def test_get_monitoring_statistics_empty(self):
        """Тест статистики мониторингов - пустой список"""
        panel = AdminPanel(123456789)
        stats = panel.get_monitoring_statistics({})
        
        assert "❌ Активных мониторингов нет" in stats
    
    def test_get_monitoring_statistics_with_data(self):
        """Тест статистики мониторингов с данными"""
        panel = AdminPanel(123456789)
        
        active_monitors = {
            12345: {
                'direction': 'minsk_ostrovets',
                'time_type': 'departure',
                'date': '2025-11-03'
            },
            67890: {
                'direction': 'ostrovets_minsk',
                'time_type': 'arrival',
                'date': '2025-11-03'
            }
        }
        
        stats = panel.get_monitoring_statistics(active_monitors)
        
        assert "Активных мониторингов: **2**" in stats
        assert "Минск → Островец" in stats
        assert "Островец → Минск" in stats
    
    def test_get_active_users_info_empty(self):
        """Тест получения информации о пользователях - пустой список"""
        panel = AdminPanel(123456789)
        user_info = panel.get_active_users_info({}, {})
        
        assert "Активных пользователей нет" in user_info
    
    def test_get_active_users_info_with_users(self):
        """Тест получения информации о пользователях с данными"""
        panel = AdminPanel(123456789)
        
        active_monitors = {
            12345: {
                'direction': 'minsk_ostrovets',
                'date': '2025-11-03'
            },
            67890: {
                'direction': 'ostrovets_minsk',
                'date': '2025-11-04'
            }
        }
        
        user_info = panel.get_active_users_info(active_monitors, {})
        
        assert "Всего пользователей:** 2" in user_info
        assert "12345" in user_info
        assert "67890" in user_info
    
    def test_get_system_logs_no_file(self):
        """Тест получения логов - файл не найден"""
        panel = AdminPanel(123456789)
        
        with patch('pathlib.Path.exists', return_value=False):
            logs = panel.get_system_logs()
            
            assert "Файл логов не найден" in logs
    
    def test_get_system_logs_empty_file(self):
        """Тест получения логов - пустой файл"""
        panel = AdminPanel(123456789)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.open', return_value=[]):
            logs = panel.get_system_logs()
            
            # Пустой файл должен обрабатываться корректно
            assert "СИСТЕМНЫЕ ЛОГИ" in logs
    
    def test_get_system_logs_with_content(self):
        """Тест получения логов с содержимым"""
        panel = AdminPanel(123456789)
        
        from io import StringIO
        mock_logs = StringIO(
            "2025-11-02 10:00:00 - INFO - Test log 1\n"
            "2025-11-02 10:01:00 - ERROR - Test error\n"
            "2025-11-02 10:02:00 - WARNING - Test warning\n"
        )
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.open', return_value=mock_logs):
            logs = panel.get_system_logs(lines=10)
            
            assert "📋 СИСТЕМНЫЕ ЛОГИ" in logs or "СИСТЕМНЫЕ ЛОГИ" in logs


class TestAdminPanelEdgeCases:
    """Тесты граничных случаев админ-панели"""
    
    def test_statistics_with_unknown_direction(self):
        """Тест статистики с неизвестным направлением"""
        panel = AdminPanel(123456789)
        
        active_monitors = {
            12345: {
                'direction': 'unknown_direction',
                'time_type': 'departure',
                'date': '2025-11-03'
            }
        }
        
        stats = panel.get_monitoring_statistics(active_monitors)
        
        assert "unknown_direction" in stats
        assert "Активных мониторингов: **1**" in stats
    
    def test_statistics_with_missing_fields(self):
        """Тест статистики с отсутствующими полями"""
        panel = AdminPanel(123456789)
        
        active_monitors = {
            12345: {}  # Пустая конфигурация
        }
        
        stats = panel.get_monitoring_statistics(active_monitors)
        
        # Должен обработать отсутствие полей без ошибок
        assert "Активных мониторингов: **1**" in stats
    
    def test_multiple_users_same_direction(self):
        """Тест статистики с несколькими пользователями одного направления"""
        panel = AdminPanel(123456789)
        
        active_monitors = {
            12345: {'direction': 'minsk_ostrovets', 'time_type': 'departure', 'date': '2025-11-03'},
            67890: {'direction': 'minsk_ostrovets', 'time_type': 'departure', 'date': '2025-11-03'},
            11111: {'direction': 'minsk_ostrovets', 'time_type': 'arrival', 'date': '2025-11-04'}
        }
        
        stats = panel.get_monitoring_statistics(active_monitors)
        
        assert "Минск → Островец: **3**" in stats
        assert "Активных мониторингов: **3**" in stats
