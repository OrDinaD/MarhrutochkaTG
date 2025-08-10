#!/usr/bin/env python3
"""
Тест парсера
"""

import asyncio
from src.parser import FinalMarshrutochkaParser

async def test_parser():
    parser = FinalMarshrutochkaParser()
    async with parser:
        result = await parser.get_all_routes('2025-07-28')
        print('=== Тест парсера ===')
        print(f'Успех: {result.get("success", False)}')
        if result.get('success'):
            minsk_routes = result.get('minsk_to_ostrovets', [])
            ostrovets_routes = result.get('ostrovets_to_minsk', [])
            print(f'Минск -> Островец: {len(minsk_routes)} рейсов')
            print(f'Островец -> Минск: {len(ostrovets_routes)} рейсов')
            
            if minsk_routes:
                route = minsk_routes[0]
                print(f'Пример рейса: {route.get("departure_time")} -> {route.get("arrival_time")}, мест: {route.get("available_seats")}')
        else:
            print(f'Ошибка: {result.get("error", "Неизвестная ошибка")}')

if __name__ == "__main__":
    asyncio.run(test_parser())
