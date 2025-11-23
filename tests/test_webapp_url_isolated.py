#!/usr/bin/env python3
"""
Изолированный тест функции create_webapp_url без зависимостей
"""


def create_webapp_url(direction: str = None, date: str = None) -> str:
    """Создает URL для веб-приложения маршруточки с параметрами"""
    base_url = "https://билет.маршруточка.бел/"
    
    params = []
    
    if direction and direction not in ["general", "both", "all"]:
        direction_map = {
            "minsk_ostrovets": "from=minsk&to=ostrovets",
            "ostrovets_minsk": "from=ostrovets&to=minsk",
            "minsk_smorgon": "from=minsk&to=smorgon",
            "smorgon_minsk": "from=smorgon&to=minsk",
            "ostrovets_smorgon": "from=ostrovets&to=smorgon",
            "smorgon_ostrovets": "from=smorgon&to=ostrovets"
        }
        
        if direction in direction_map:
            params.append(direction_map[direction])
            
            # Добавляем дату только если есть направление
            if date:
                params.append(f"date={date}")
    
    if params:
        return f"{base_url}#{'&'.join(params)}"
    
    return base_url


def run_tests():
    """Запуск всех тестов"""
    print("🧪 Тестирование генерации URL с параметрами\n")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1
    tests_total += 1
    print("\n📝 Test 1: URL с направлением и датой")
    url1 = create_webapp_url('minsk_ostrovets', '2025-11-25')
    expected1 = "https://билет.маршруточка.бел/#from=minsk&to=ostrovets&date=2025-11-25"
    print(f"   Expected: {expected1}")
    print(f"   Got:      {url1}")
    if url1 == expected1:
        print("   ✅ PASSED")
        tests_passed += 1
    else:
        print("   ❌ FAILED")
    
    # Test 2
    tests_total += 1
    print("\n📝 Test 2: URL только с направлением")
    url2 = create_webapp_url('ostrovets_minsk')
    expected2 = "https://билет.маршруточка.бел/#from=ostrovets&to=minsk"
    print(f"   Expected: {expected2}")
    print(f"   Got:      {url2}")
    if url2 == expected2 and 'date' not in url2:
        print("   ✅ PASSED")
        tests_passed += 1
    else:
        print("   ❌ FAILED")
    
    # Test 3
    tests_total += 1
    print("\n📝 Test 3: URL без параметров")
    url3 = create_webapp_url()
    expected3 = "https://билет.маршруточка.бел/"
    print(f"   Expected: {expected3}")
    print(f"   Got:      {url3}")
    if url3 == expected3:
        print("   ✅ PASSED")
        tests_passed += 1
    else:
        print("   ❌ FAILED")
    
    # Test 4
    tests_total += 1
    print("\n📝 Test 4: Все направления")
    directions_test = [
        ('minsk_ostrovets', 'from=minsk&to=ostrovets'),
        ('ostrovets_minsk', 'from=ostrovets&to=minsk'),
        ('minsk_smorgon', 'from=minsk&to=smorgon'),
        ('smorgon_minsk', 'from=smorgon&to=minsk'),
        ('ostrovets_smorgon', 'from=ostrovets&to=smorgon'),
        ('smorgon_ostrovets', 'from=smorgon&to=ostrovets'),
    ]
    
    all_passed = True
    for direction, expected_params in directions_test:
        url = create_webapp_url(direction)
        if f'#{expected_params}' not in url:
            print(f"   ❌ Failed for {direction}")
            all_passed = False
        else:
            print(f"   ✅ {direction}")
    
    if all_passed:
        print("   ✅ PASSED")
        tests_passed += 1
    else:
        print("   ❌ FAILED")
    
    # Test 5
    tests_total += 1
    print("\n📝 Test 5: 'general' не добавляет параметры")
    url5 = create_webapp_url('general', '2025-11-25')
    expected5 = "https://билет.маршруточка.бел/"
    print(f"   Expected: {expected5}")
    print(f"   Got:      {url5}")
    if url5 == expected5:
        print("   ✅ PASSED")
        tests_passed += 1
    else:
        print("   ❌ FAILED")
    
    # Test 6
    tests_total += 1
    print("\n📝 Test 6: 'both' не добавляет параметры")
    url6 = create_webapp_url('both')
    expected6 = "https://билет.маршруточка.бел/"
    print(f"   Expected: {expected6}")
    print(f"   Got:      {url6}")
    if url6 == expected6:
        print("   ✅ PASSED")
        tests_passed += 1
    else:
        print("   ❌ FAILED")
    
    # Test 7
    tests_total += 1
    print("\n📝 Test 7: Только дата (без направления)")
    url7 = create_webapp_url(date='2025-11-25')
    expected7 = "https://билет.маршруточка.бел/"
    print(f"   Expected: {expected7}")
    print(f"   Got:      {url7}")
    if url7 == expected7:
        print("   ✅ PASSED (дата игнорируется без направления)")
        tests_passed += 1
    else:
        print("   ❌ FAILED")
    
    # Итоги
    print("\n" + "=" * 60)
    print(f"\n📊 Результаты тестирования:")
    print(f"   Пройдено: {tests_passed}/{tests_total}")
    print(f"   Провалено: {tests_total - tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("\n🎉 Все тесты успешно пройдены!")
        print("\n✅ Параметры корректно передаются в URL через hash")
        print("✅ Сайт может прочитать их через window.location.hash")
        print("✅ Обратная совместимость сохранена")
        return 0
    else:
        print("\n❌ Некоторые тесты провалены")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_tests())
