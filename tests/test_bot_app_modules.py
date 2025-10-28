"""Тесты для модулей bot_app."""
import pytest
from types import SimpleNamespace

from telegram import InlineKeyboardMarkup

from bot_app.conversation import CONFIRM_MONITORING
from bot_app.handlers.monitoring import handle_custom_time_range_input
from bot_app.handlers.search import format_specific_routes
from bot_app.keyboards import create_webapp_keyboard
from bot_app.monitoring_service import (
    check_time_criteria,
    filter_routes_by_criteria,
    format_monitor_config,
)
from bot_app import state


@pytest.fixture(autouse=True)
def reset_state():
    """Сбрасывает in-memory хранилища перед тестом."""
    state.user_data_store.clear()
    state.active_monitors.clear()
    yield
    state.user_data_store.clear()
    state.active_monitors.clear()


def test_format_monitor_config_contains_keys():
    config = {
        "date": "2025-01-15",
        "direction": "minsk_ostrovets",
        "time_type": "departure",
        "time_range": "07:00-09:00",
    }
    result = format_monitor_config(config)
    assert "📅" in result and "🛣️" in result and "⏰" in result


def test_filter_routes_by_criteria_filters_by_time():
    routes_data = {
        "minsk_to_ostrovets": [
            {"available_seats": 5, "departure_time": "08:30", "arrival_time": "10:30"},
            {"available_seats": 0, "departure_time": "08:45", "arrival_time": "10:45"},
            {"available_seats": 2, "departure_time": "12:00", "arrival_time": "14:00"},
        ],
        "success": True,
    }
    config = {
        "direction": "minsk_ostrovets",
        "time_range": "08:00-09:00",
        "time_type": "departure",
    }
    result = filter_routes_by_criteria(routes_data, config)
    assert len(result) == 1
    assert result[0]["departure_time"] == "08:30"


@pytest.mark.parametrize(
    "time_range, route_time, expected",
    [
        ("22:00-02:00", "23:30", True),
        ("22:00-02:00", "03:00", False),
        ("07:00-09:00", "08:00", True),
    ],
)
def test_check_time_criteria_handles_ranges(time_range, route_time, expected):
    route = {"departure_time": route_time}
    config = {"time_range": time_range, "time_type": "departure"}
    assert check_time_criteria(route, config) is expected


def test_create_webapp_keyboard_contains_button():
    keyboard = create_webapp_keyboard("minsk_ostrovets", "2025-01-15")
    assert isinstance(keyboard, InlineKeyboardMarkup)
    buttons = [button.text for row in keyboard.inline_keyboard for button in row]
    assert any("Открыть" in text for text in buttons)


def test_format_specific_routes_without_header():
    routes = [
        {
            "departure_time": "08:00",
            "arrival_time": "09:30",
            "available_seats": 3,
        }
    ]
    message = format_specific_routes(routes, "Минск", "Островец", "2025-01-15", include_header=False)
    assert "📅" not in message
    assert "08:00" in message


@pytest.mark.asyncio
async def test_handle_custom_time_range_input_accepts_valid(monkeypatch):
    user_id = 42
    state.user_data_store[user_id] = {
        "date": "2025-01-15",
        "direction": "minsk_ostrovets",
        "time_type": "departure",
    }

    sent_messages = []

    async def fake_reply_text(*args, **kwargs):
        sent_messages.append((args, kwargs))

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(text="07:00-09:00", reply_text=fake_reply_text),
    )
    context = SimpleNamespace()

    result = await handle_custom_time_range_input(update, context)
    assert result == CONFIRM_MONITORING
    assert state.user_data_store[user_id]["time_range"] == "07:00-09:00"
    assert sent_messages, "Ожидалось подтверждающее сообщение"
