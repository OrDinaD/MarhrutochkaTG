"""Инициализация парсера маршруточки."""
from typing import Optional

from src.utils import FinalMarshrutochkaParser

from . import state


async def init_parser() -> FinalMarshrutochkaParser:
    """Инициализирует и возвращает парсер, если он ещё не создан."""
    if state.parser is None:
        state.parser = FinalMarshrutochkaParser()
        await state.parser.__aenter__()
    return state.parser  # type: ignore[return-value]


def get_parser() -> Optional[FinalMarshrutochkaParser]:
    """Возвращает текущий экземпляр парсера."""
    return state.parser  # type: ignore[return-value]


__all__ = ["init_parser", "get_parser"]
