import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_button_callback_confirms_monitoring_without_conversation(monkeypatch):
    bot = importlib.import_module("bot")

    user_id = 4242
    bot.user_data_store[user_id] = {
        "date": "2025-01-01",
        "direction": "minsk_ostrovets",
        "time_type": "departure",
        "time_range": "07:00-09:00",
    }

    bot.active_monitors.pop(user_id, None)
    bot.user_manager.active_monitors.pop(user_id, None)
    bot.job_queue = None

    safe_edit_mock = AsyncMock()
    monkeypatch.setattr(bot, "safe_edit_message", safe_edit_mock)
    monkeypatch.setattr(bot, "safe_answer_callback", AsyncMock())

    class DummyMessage:
        def __init__(self, chat_id: int):
            self.chat_id = chat_id

    class DummyQuery:
        def __init__(self, data: str):
            self.data = data
            self.id = "dummy"
            self.from_user = SimpleNamespace(id=user_id)
            self.message = DummyMessage(chat_id=111)

    class DummyUpdate:
        def __init__(self, data: str):
            self.callback_query = DummyQuery(data)

    class DummyContext(SimpleNamespace):
        def __init__(self):
            super().__init__(user_data={}, bot_data={})

    update = DummyUpdate("confirm_yes")
    context = DummyContext()

    result = await bot.button_callback(update, context)

    assert result == bot.ConversationHandler.END
    assert user_id in bot.active_monitors
    assert bot.active_monitors[user_id]["time_range"] == "07:00-09:00"

    safe_edit_mock.assert_awaited()

