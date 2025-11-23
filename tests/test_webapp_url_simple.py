#!/usr/bin/env python3
"""
Простой скрипт для тестирования URL параметров
"""
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.bot import create_webapp_url
from src.utils.keyboards import create_webapp_url_helper


def test_url_generation():
    """Тестирование генерации URL"""
    print("🧪 Тестирование генерации URL с параметрами\n")
    
    # Test 1
    print("Test 1: URL с направлением и датой")
    url1 = create_webapp_url('minsk_ostrovets', '2025-11-25')
    print(f"   Result: {url1}")
    assert '#from=minsk&to=ostrovets&date=2025-11-25' in url1
    print("   ✅ Passed\n")
    
    # Test 2
    print("Test 2: URL только с направлением")
    url2 = create_webapp_url('ostrovets_minsk')
    print(f"   Result: {url2}")
    assert '#from=ostrovets&to=minsk' in url2
    assert 'date' not in url2
    print("   ✅ Passed\n")
    
    # Test 3
    print("Test 3: URL без параметров")
    url3 = create_webapp_url()
    print(f"   Result: {url3}")
    assert url3 == 'https://билет.маршруточка.бел/'
    assert '#' not in url3
    print("   ✅ Passed\n")
    
    # Test 4
    print("Test 4: Все направления")
    directions = [
        ('minsk_ostrovets', 'from=minsk&to=ostrovets'),
        ('ostrovets_minsk', 'from=ostrovets&to=minsk'),
        ('minsk_smorgon', 'from=minsk&to=smorgon'),
        ('smorgon_minsk', 'from=smorgon&to=minsk'),
        ('ostrovets_smorgon', 'from=ostrovets&to=smorgon'),
        ('smorgon_ostrovets', 'from=smorgon&to=ostrovets'),
    ]
    
    for direction, expected in directions:
        url = create_webapp_url(direction)
        assert f'#{expected}' in url
        print(f"   {direction}: ✅")
    print("   ✅ Passed\n")
    
    # Test 5
    print("Test 5: Helper функция из keyboards")
    url5 = create_webapp_url_helper('minsk_ostrovets', '2025-11-25')
    print(f"   Result: {url5}")
    assert '#from=minsk&to=ostrovets&date=2025-11-25' in url5
    print("   ✅ Passed\n")
    
    # Test 6
    print("Test 6: 'general' и 'both' не добавляют параметры")
    url6a = create_webapp_url('general', '2025-11-25')
    url6b = create_webapp_url('both')
    print(f"   general: {url6a}")
    print(f"   both: {url6b}")
    assert url6a == 'https://билет.маршруточка.бел/'
    assert url6b == 'https://билет.маршруточка.бел/'
    print("   ✅ Passed\n")
    
    print("=" * 60)
    print("🎉 Все тесты пройдены успешно!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_url_generation()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
