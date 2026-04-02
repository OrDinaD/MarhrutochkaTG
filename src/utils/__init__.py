"""Utility exports exposed at package level."""

# Новый парсер на основе API BusPro.by
try:
    from ..scraper.buspro_api_parser import BusproAPIParser
    FinalMarshrutochkaParser = BusproAPIParser  # Alias для обратной совместимости
except ImportError:
    from .parser import FinalMarshrutochkaParser

__all__ = ['FinalMarshrutochkaParser', 'BusproAPIParser']
