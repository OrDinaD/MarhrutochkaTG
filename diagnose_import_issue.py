#!/usr/bin/env python3
"""
Диагностика проблемы с import json
"""
import sys
import os

print("🔍 Диагностика импортов...")

# Добавляем путь
sys.path.append('src')

# Тестируем импорт json на уровне модуля
try:
    import json
    print("✅ Импорт json на уровне файла работает")
except Exception as e:
    print(f"❌ Ошибка импорта json: {e}")

# Читаем начало bot.py и проверим все импорты
try:
    with open('src/bot.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()[:50]  # Первые 50 строк
    
    imports = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if line.startswith('import ') or line.startswith('from '):
            imports.append(f"Строка {i}: {line}")
    
    print(f"\n📋 Найдено {len(imports)} импортов:")
    for imp in imports:
        print(f"  {imp}")
    
    # Проверяем специально json
    json_imports = [imp for imp in imports if 'json' in imp]
    if json_imports:
        print(f"\n✅ JSON импорты найдены: {json_imports}")
    else:
        print("\n❌ JSON импорты НЕ найдены!")
    
except Exception as e:
    print(f"❌ Ошибка чтения файла: {e}")

# Тестируем функцию load_active_monitors отдельно
print("\n🧪 Тестирование функции load_active_monitors...")

def test_load_monitors():
    """Тест функции без telegram зависимостей"""
    import json
    import os
    
    # Определяем переменные
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
    DATA_FILE = os.path.join(DATA_DIR, 'monitors.json')
    active_monitors = {}
    
    # Копируем логику функции
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            active_monitors = {int(k): v for k, v in data.items()}
            print(f"✅ Мониторинги загружены: {len(active_monitors)} пользователей")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки мониторингов: {e}")
            return False
    else:
        print(f"⚠️ Файл {DATA_FILE} не существует")
        return True

success = test_load_monitors()

print("\n📊 Результат диагностики:")
if success:
    print("✅ Проблема НЕ в импорте json или логике загрузки")
    print("🔍 Возможные причины:")
    print("  1. Проблемы с Railway environment")
    print("  2. Конфликт версий библиотек")
    print("  3. Проблемы с порядком инициализации")
else:
    print("❌ Проблема воспроизведена локально")
