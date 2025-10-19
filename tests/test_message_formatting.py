import importlib

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_perform_route_search_marks_via_smorgon(monkeypatch):
    bot = importlib.import_module("bot")

    monkeypatch.setattr(bot, 'init_parser', AsyncMock())

    class DummyParser:
        async def get_all_routes(self, date):
            return {
                'ostrovets_to_minsk': [
                    {
                        'departure_time': '08:00',
                        'arrival_time': '10:00',
                        'duration': '2 ч',
                        'available_seats': 5,
                        'via_smorgon': True,
                        'via_oshmiany': False,
                    }
                ],
                'success': True,
            }

    monkeypatch.setattr(bot, 'parser', DummyParser(), raising=False)

    send_mock = AsyncMock()
    monkeypatch.setattr(bot, 'safe_edit_message', send_mock)

    await bot.perform_route_search(object(), user_id=1, from_city="Островец", to_city="Минск", date="2025-01-01")

    send_mock.assert_awaited_once()
    message = send_mock.await_args.args[1]
    assert "через Сморгонь" in message
    assert "через Ошмяны" not in message


@pytest.mark.asyncio
async def test_perform_route_search_marks_via_oshmiany(monkeypatch):
    bot = importlib.import_module("bot")

    monkeypatch.setattr(bot, 'init_parser', AsyncMock())

    class DummyParser:
        async def get_all_routes(self, date):
            return {
                'minsk_to_ostrovets': [
                    {
                        'departure_time': '12:00',
                        'arrival_time': '15:00',
                        'duration': '3 ч',
                        'available_seats': 2,
                        'via_smorgon': False,
                        'via_oshmiany': True,
                    }
                ],
                'success': True,
            }

    monkeypatch.setattr(bot, 'parser', DummyParser(), raising=False)

    send_mock = AsyncMock()
    monkeypatch.setattr(bot, 'safe_edit_message', send_mock)

    await bot.perform_route_search(object(), user_id=2, from_city="Минск", to_city="Островец", date="2025-01-02")

    send_mock.assert_awaited_once()
    message = send_mock.await_args.args[1]
    assert "через Ошмяны" in message
    assert "через Сморгонь" not in message
