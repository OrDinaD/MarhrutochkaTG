import asyncio
import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.parser import FinalMarshrutochkaParser

class FakeResponse:
    def __init__(self, html):
        self.status = 200
        self._html = html
    async def json(self):
        return {"html": self._html}
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.mark.asyncio
async def test_cache_enabled(monkeypatch):
    parser = FinalMarshrutochkaParser(enable_cache=True)
    call_count = 0
    async with parser:
        def fake_get(url, params=None):
            nonlocal call_count
            call_count += 1
            return FakeResponse("<div></div>")
        monkeypatch.setattr(parser.session, "get", fake_get)
        monkeypatch.setattr(parser, "parse_html_schedule", lambda html, f, t, d: [html])
        await parser.search_routes("Минск", "Островец", "2024-01-01")
        await parser.search_routes("Минск", "Островец", "2024-01-01")
    assert call_count == 1

@pytest.mark.asyncio
async def test_cache_disabled(monkeypatch):
    parser = FinalMarshrutochkaParser(enable_cache=False)
    call_count = 0
    async with parser:
        def fake_get(url, params=None):
            nonlocal call_count
            call_count += 1
            return FakeResponse("<div></div>")
        monkeypatch.setattr(parser.session, "get", fake_get)
        monkeypatch.setattr(parser, "parse_html_schedule", lambda html, f, t, d: [html])
        await parser.search_routes("Минск", "Островец", "2024-01-01")
        await parser.search_routes("Минск", "Островец", "2024-01-01")
    assert call_count == 2
