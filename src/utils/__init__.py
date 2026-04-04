"""Utility exports exposed at package level."""

# Новый парсер на основе API BusPro.by - используем его по умолчанию
from scraper.buspro_api_parser import BusproAPIParser
FinalMarshrutochkaParser = BusproAPIParser  # Alias для обратной совместимости

__all__ = ['FinalMarshrutochkaParser', 'BusproAPIParser']
