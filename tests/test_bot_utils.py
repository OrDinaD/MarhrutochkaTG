import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot import (
    format_monitor_config,
    check_time_criteria,
    format_routes_message,
    filter_routes_by_criteria,
    create_webapp_url,
    create_webapp_keyboard,
)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo


def test_format_monitor_config():
    config = {
        'date': '2025-01-15',
        'direction': 'minsk_ostrovets',
        'time_type': 'departure',
        'time_range': '08:00-12:00'
    }
    expected_output = (
        "📅 **Дата:** 2025-01-15\n"
        "🛣️ **Направление:** Минск → Островец\n"
        "⏰ **Время:** отправления\n"
        "🕐 **Диапазон:** 08:00-12:00\n"
        "🔔 **Проверка:** каждые 5 минут"
    )
    assert format_monitor_config(config) == expected_output

def test_check_time_criteria():
    # Test case 1: Time within range
    route = {'departure_time': '10:00'}
    config = {'time_type': 'departure', 'time_range': '08:00-12:00'}
    assert check_time_criteria(route, config) is True

    # Test case 2: Time outside range
    route = {'departure_time': '14:00'}
    config = {'time_type': 'departure', 'time_range': '08:00-12:00'}
    assert check_time_criteria(route, config) is False

    # Test case 3: Time on edge of range
    route = {'departure_time': '08:00'}
    config = {'time_type': 'departure', 'time_range': '08:00-12:00'}
    assert check_time_criteria(route, config) is True

    # Test case 4: Time range across midnight
    route = {'departure_time': '23:00'}
    config = {'time_type': 'departure', 'time_range': '22:00-02:00'}
    assert check_time_criteria(route, config) is True

    # Test case 5: Time range across midnight (after midnight)
    route = {'departure_time': '01:00'}
    config = {'time_type': 'departure', 'time_range': '22:00-02:00'}
    assert check_time_criteria(route, config) is True

    # Test case 6: 'any' time type
    route = {'departure_time': '10:00'}
    config = {'time_type': 'any', 'time_range': '08:00-12:00'}
    assert check_time_criteria(route, config) is True

    # Test case 7: Invalid time format in route
    route = {'departure_time': 'invalid-time'}
    config = {'time_type': 'departure', 'time_range': '08:00-12:00'}
    assert check_time_criteria(route, config) is True

def test_format_routes_message():
    routes_data = {
        'success': True,
        'minsk_to_ostrovets': [],
        'ostrovets_to_minsk': [],
        'minsk_to_smorgon': [],
        'smorgon_to_minsk': [],
        'ostrovets_to_smorgon': [],
        'smorgon_to_ostrovets': [],
    }
    date = '2025-01-15'
    message = format_routes_message(routes_data, date)
    assert isinstance(message, str)

def test_filter_routes_by_criteria():
    routes_data = {
        'minsk_to_ostrovets': [
            {'available_seats': 5, 'departure_time': '10:00'},
            {'available_seats': 0, 'departure_time': '14:00'},
        ],
        'ostrovets_to_minsk': [
            {'available_seats': 3, 'departure_time': '18:00'},
        ]
    }

    # Test case 1: Filter by direction 'minsk_ostrovets'
    config = {'direction': 'minsk_ostrovets', 'time_range': 'any'}
    filtered_routes = filter_routes_by_criteria(routes_data, config)
    assert len(filtered_routes) == 1
    assert filtered_routes[0]['departure_time'] == '10:00'

    # Test case 2: Filter by direction 'both'
    config = {'direction': 'both', 'time_range': 'any'}
    filtered_routes = filter_routes_by_criteria(routes_data, config)
    assert len(filtered_routes) == 2

    # Test case 3: Filter by time
    config = {'direction': 'both', 'time_range': '08:00-12:00', 'time_type': 'departure'}
    filtered_routes = filter_routes_by_criteria(routes_data, config)
    assert len(filtered_routes) == 1
    assert filtered_routes[0]['departure_time'] == '10:00'

    # Test case 4: No suitable routes
    config = {'direction': 'both', 'time_range': '14:00-16:00', 'time_type': 'departure'}
    filtered_routes = filter_routes_by_criteria(routes_data, config)
    assert len(filtered_routes) == 0

def test_create_webapp_url():
    # Test with direction and date
    url = create_webapp_url("minsk_ostrovets", "2025-11-25")
    assert "билет.маршруточка.бел" in url
    assert "#from=minsk&to=ostrovets&date=2025-11-25" in url
    
    # Test with only direction
    url = create_webapp_url("ostrovets_minsk")
    assert "#from=ostrovets&to=minsk" in url
    
    # Test with general (no params)
    url = create_webapp_url("general")
    assert url == "https://билет.маршруточка.бел/"
    
    # Test without params
    url = create_webapp_url()
    assert url == "https://билет.маршруточка.бел/"

def test_create_webapp_keyboard():
    # Test case 1: Specific direction
    keyboard = create_webapp_keyboard("minsk_ostrovets")
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 1
    assert isinstance(keyboard.inline_keyboard[0][0], InlineKeyboardButton)
    assert keyboard.inline_keyboard[0][0].text == "🌐 Открыть сайт бронирования"
    assert isinstance(keyboard.inline_keyboard[0][0].web_app, WebAppInfo)

    # Test case 2: Direction with smorgon
    keyboard = create_webapp_keyboard("minsk_smorgon")
    assert len(keyboard.inline_keyboard) == 2
    assert keyboard.inline_keyboard[1][0].text == "ℹ️ Информация о Сморгони"

    # Test case 3: 'both' direction
    keyboard = create_webapp_keyboard("both")
    assert len(keyboard.inline_keyboard) == 1
    assert keyboard.inline_keyboard[0][0].text == "🚌 Открыть сайт маршруточки"

    # Test case 4: No direction
    keyboard = create_webapp_keyboard()
    assert len(keyboard.inline_keyboard) == 1
    assert keyboard.inline_keyboard[0][0].text == "🚌 Открыть сайт маршруточки"

    # Test case 5: With additional buttons
    additional_buttons = [[InlineKeyboardButton("Test", callback_data="test")]]
    keyboard = create_webapp_keyboard("minsk_ostrovets", additional_buttons=additional_buttons)
    assert len(keyboard.inline_keyboard) == 2
    assert keyboard.inline_keyboard[1][0].text == "Test"
