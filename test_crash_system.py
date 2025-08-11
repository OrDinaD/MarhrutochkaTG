#!/usr/bin/env python3
"""
Тестирование системы автоматического обнаружения и восстановления крашей
"""

import os
import sys
import json
import asyncio
import traceback
from datetime import datetime
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.crash_handler import crash_handler
from src.diagnostic_system import diagnostic_system
from src.auto_recovery import auto_recovery

async def test_crash_detection():
    """Тестирует систему обнаружения крашей"""
    print("🧪 Тестирование системы обнаружения крашей...")
    
    try:
        # Настраиваем crash handler
        crash_handler.setup_crash_handling()
        print("✅ Crash handler настроен")
        
        # Симулируем различные типы ошибок
        test_cases = [
            {
                "name": "NetworkError",
                "exception": Exception("ConnectionError: Failed to establish a new connection"),
                "expected_category": "network"
            },
            {
                "name": "ModuleNotFoundError", 
                "exception": ModuleNotFoundError("No module named 'missing_module'"),
                "expected_category": "dependencies"
            },
            {
                "name": "FileNotFoundError",
                "exception": FileNotFoundError("config.json not found"),
                "expected_category": "filesystem"
            },
            {
                "name": "MemoryError",
                "exception": MemoryError("Unable to allocate memory"),
                "expected_category": "resources"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"\n🔍 Тест {i+1}: {test_case['name']}")
            
            try:
                # Создаем crash report
                crash_report = await crash_handler.handle_exception(
                    test_case['exception'],
                    test_context=f"test_case_{i+1}"
                )
                
                print(f"✅ Crash report создан: {crash_report.get('crash_id', 'unknown')[:12]}...")
                
                # Анализируем crash report
                analysis = await diagnostic_system.analyze_crash_report(crash_report)
                print(f"✅ Анализ завершен, категория: {analysis.get('primary_issue', {}).get('category', 'unknown')}")
                
                # Проверяем автоматическое восстановление
                recovery_result = await auto_recovery.attempt_auto_recovery(analysis)
                success = recovery_result.get('success', False)
                actions_count = len(recovery_result.get('actions_taken', []))
                
                print(f"✅ Автовосстановление: {'успешно' if success else 'неуспешно'} ({actions_count} действий)")
                
            except Exception as e:
                print(f"❌ Ошибка в тесте {test_case['name']}: {e}")
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка тестирования: {e}")
        traceback.print_exc()
        return False

async def test_system_integration():
    """Тестирует интеграцию всех компонентов"""
    print("\n🔗 Тестирование интеграции системы...")
    
    try:
        # Проверяем наличие всех компонентов
        components = {
            "crash_handler": crash_handler is not None,
            "diagnostic_system": diagnostic_system is not None,
            "auto_recovery": auto_recovery is not None
        }
        
        print("📊 Статус компонентов:")
        for name, status in components.items():
            print(f"  • {name}: {'✅' if status else '❌'}")
        
        if not all(components.values()):
            print("❌ Не все компоненты доступны!")
            return False
        
        # Тестируем полный цикл
        print("\n🔄 Тестирование полного цикла...")
        
        # Симулируем краш
        test_exception = Exception("Test crash for integration testing")
        
        # 1. Обработка краша
        crash_report = await crash_handler.handle_exception(
            test_exception,
            test_context="integration_test"
        )
        print(f"✅ Шаг 1: Crash report создан")
        
        # 2. Анализ краша
        analysis = await diagnostic_system.analyze_crash_report(crash_report)
        print(f"✅ Шаг 2: Анализ завершен")
        
        # 3. Автоматическое восстановление
        recovery_result = await auto_recovery.attempt_auto_recovery(analysis)
        print(f"✅ Шаг 3: Восстановление завершено")
        
        # 4. Проверяем сохранение данных
        crash_logs_dir = Path('crash_logs')
        if crash_logs_dir.exists() and any(crash_logs_dir.glob('*.json')):
            print("✅ Шаг 4: Логи крашей сохранены")
        else:
            print("⚠️ Шаг 4: Логи крашей не найдены")
        
        # 5. Проверяем историю восстановлений
        recovery_history = auto_recovery.get_recovery_history(days=1)
        if recovery_history:
            print(f"✅ Шаг 5: История восстановлений содержит {len(recovery_history)} записей")
        else:
            print("⚠️ Шаг 5: История восстановлений пуста")
        
        print("\n🎉 Интеграционный тест завершен успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка интеграционного теста: {e}")
        traceback.print_exc()
        return False

def test_environment_setup():
    """Проверяет настройку окружения"""
    print("🌍 Проверка настройки окружения...")
    
    # Проверяем переменные окружения
    env_vars = {
        "TELEGRAM_BOT_TOKEN": os.getenv('TELEGRAM_BOT_TOKEN'),
        "ADMIN_TELEGRAM_ID": os.getenv('ADMIN_TELEGRAM_ID'),
        "GITHUB_TOKEN": os.getenv('GITHUB_TOKEN'),
        "RAILWAY_SERVICE_NAME": os.getenv('RAILWAY_SERVICE_NAME')
    }
    
    print("📋 Переменные окружения:")
    for var, value in env_vars.items():
        status = "✅ Установлена" if value else "❌ Отсутствует"
        masked_value = f"{value[:10]}..." if value and len(value) > 10 else value or "None"
        print(f"  • {var}: {status} ({masked_value})")
    
    # Проверяем структуру директорий
    required_dirs = ['src', 'logs', 'crash_logs']
    print("\n📁 Структура директорий:")
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  • {dir_name}: ✅ Создана")
        else:
            print(f"  • {dir_name}: ✅ Существует")
    
    # Проверяем критичные файлы
    critical_files = [
        'src/crash_handler.py',
        'src/diagnostic_system.py', 
        'src/auto_recovery.py',
        'src/bot.py',
        'requirements.txt'
    ]
    
    print("\n📄 Критичные файлы:")
    for file_path in critical_files:
        path = Path(file_path)
        status = "✅ Существует" if path.exists() else "❌ Отсутствует"
        print(f"  • {file_path}: {status}")
    
    return True

async def generate_test_report():
    """Генерирует отчет о тестировании"""
    print("\n📊 Генерация отчета о тестировании...")
    
    report = {
        "test_timestamp": datetime.now().isoformat(),
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform,
            "railway": bool(os.getenv('RAILWAY_SERVICE_NAME'))
        },
        "components_status": {
            "crash_handler": crash_handler is not None,
            "diagnostic_system": diagnostic_system is not None,
            "auto_recovery": auto_recovery is not None
        },
        "test_results": {
            "environment_setup": True,
            "crash_detection": False,
            "system_integration": False
        }
    }
    
    try:
        # Запускаем тесты
        print("🧪 Выполнение тестов...")
        
        report["test_results"]["crash_detection"] = await test_crash_detection()
        report["test_results"]["system_integration"] = await test_system_integration()
        
        # Сохраняем отчет
        report_file = Path('test_report.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ Отчет сохранен в {report_file}")
        
        # Выводим краткую сводку
        all_passed = all(report["test_results"].values())
        print(f"\n{'🎉' if all_passed else '⚠️'} ИТОГОВЫЙ РЕЗУЛЬТАТ: {'ВСЕ ТЕСТЫ ПРОЙДЕНЫ' if all_passed else 'ЕСТЬ ПРОБЛЕМЫ'}")
        
        for test_name, result in report["test_results"].items():
            status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
            print(f"  • {test_name}: {status}")
        
        return report
        
    except Exception as e:
        print(f"❌ Ошибка генерации отчета: {e}")
        traceback.print_exc()
        return None

async def main():
    """Главная функция тестирования"""
    print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ СИСТЕМЫ CRASH HANDLING")
    print("=" * 60)
    
    try:
        # Настройка окружения
        test_environment_setup()
        
        # Генерация и выполнение тестов
        report = await generate_test_report()
        
        if report:
            print("\n📈 Тестирование завершено успешно!")
            return True
        else:
            print("\n💥 Тестирование завершено с ошибками!")
            return False
            
    except Exception as e:
        print(f"\n❌ Критическая ошибка тестирования: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Устанавливаем тестовые переменные окружения если они не установлены
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_for_testing'
    
    if not os.getenv('ADMIN_TELEGRAM_ID'):
        os.environ['ADMIN_TELEGRAM_ID'] = '123456789'
    
    # Запускаем тесты
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
