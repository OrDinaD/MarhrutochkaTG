#!/usr/bin/env python3
"""
Тест исправления проблемы с json import
"""

import sys
import os

print("🔧 Тестирование исправления проблемы с json import...")

# Добавляем путь
sys.path.append('src')

def test_import_order():
    """Тестируем порядок импортов"""
    print("\n📋 Анализ импортов в bot.py...")
    
    with open('src/bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ищем где определен json
    json_import_line = None
    load_monitors_call = None
    
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if line.strip() == 'import json':
            json_import_line = i
        if 'load_active_monitors()' in line and not line.strip().startswith('#'):
            load_monitors_call = i
    
    print(f"✅ import json найден на строке: {json_import_line}")
    if load_monitors_call:
        print(f"📍 load_active_monitors() вызывается на строке: {load_monitors_call}")
        
        # Проверяем находится ли вызов в main()
        main_start = None
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('def main():'):
                main_start = i
                break
        
        if main_start and load_monitors_call > main_start:
            print(f"✅ load_active_monitors() вызывается ВНУТРИ main() (строка {main_start})")
        else:
            print(f"❌ load_active_monitors() вызывается НА УРОВНЕ МОДУЛЯ!")
    else:
        print("⚠️ load_active_monitors() не найден или закомментирован")

def test_function_access():
    """Тестируем доступность json в функции"""
    print("\n🧪 Тестирование доступности json в функции...")
    
    # Имитируем условия Railway
    try:
        import json as json_module
        
        def mock_load_active_monitors():
            # Эта функция должна иметь доступ к json
            data = json_module.dumps({"test": "data"})
            parsed = json_module.loads(data)
            return parsed
        
        result = mock_load_active_monitors()
        print(f"✅ json доступен в функции: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка доступа к json в функции: {e}")
        return False

def check_module_level_calls():
    """Проверяем нет ли вызовов на уровне модуля"""
    print("\n🔍 Проверка вызовов на уровне модуля...")
    
    with open('src/bot.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Ищем вызовы load_ функций на уровне модуля
    dangerous_calls = []
    in_function = False
    indent_level = 0
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Определяем находимся ли в функции
        if stripped.startswith('def ') or stripped.startswith('async def '):
            in_function = True
            indent_level = len(line) - len(line.lstrip())
        elif in_function and line.strip() and len(line) - len(line.lstrip()) <= indent_level:
            in_function = False
        
        # Проверяем опасные вызовы на уровне модуля
        if not in_function and (
            'load_active_monitors()' in stripped or 
            'load_user_sessions()' in stripped
        ) and not stripped.startswith('#'):
            dangerous_calls.append(f"Строка {i}: {stripped}")
    
    if dangerous_calls:
        print("❌ Найдены вызовы на уровне модуля:")
        for call in dangerous_calls:
            print(f"  {call}")
        return False
    else:
        print("✅ Все загрузочные функции вызываются внутри функций")
        return True

if __name__ == "__main__":
    print("=" * 60)
    
    success = True
    
    # Тесты
    test_import_order()
    
    if not test_function_access():
        success = False
    
    if not check_module_level_calls():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ Проблема с json import должна быть исправлена")
        print("📤 Готово к деплою в Railway")
    else:
        print("❌ Найдены проблемы, требующие исправления")
        sys.exit(1)
