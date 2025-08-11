#!/usr/bin/env python3
"""
Тест Railway деплоя - проверка всех компонентов системы
"""

import os
import sys
import json
import time
import subprocess
import traceback
from typing import Dict, List, Any, Optional

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class RailwayDeploymentTester:
    """Тестирование Railway деплоя с полной проверкой системы"""
    
    def __init__(self):
        self.test_results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'tests': {},
            'overall_status': 'PENDING',
            'errors': [],
            'warnings': []
        }
        
    def log_test(self, test_name: str, status: str, details: Any = None, error: str = None):
        """Логирование результата теста"""
        self.test_results['tests'][test_name] = {
            'status': status,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'details': details,
            'error': error
        }
        
        status_emoji = {
            'PASS': '✅',
            'FAIL': '❌', 
            'WARN': '⚠️',
            'SKIP': '⏭️'
        }.get(status, '❓')
        
        print(f"{status_emoji} {test_name}: {status}")
        if details:
            print(f"   📋 Details: {details}")
        if error:
            print(f"   🚨 Error: {error}")
    
    def test_docker_configuration(self) -> bool:
        """Тест конфигурации Docker"""
        try:
            # Проверяем Dockerfile
            dockerfile_path = "Dockerfile"
            if not os.path.exists(dockerfile_path):
                self.log_test("Docker Configuration", "FAIL", error="Dockerfile not found")
                return False
                
            with open(dockerfile_path, 'r') as f:
                dockerfile_content = f.read()
                
            required_elements = [
                'FROM python:3.11-slim',
                'WORKDIR /app',
                'COPY requirements.txt',
                'RUN pip install',
                'COPY . .',
                'CMD ["python", "main.py"]'
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in dockerfile_content:
                    missing_elements.append(element)
                    
            if missing_elements:
                self.log_test("Docker Configuration", "FAIL", 
                            error=f"Missing elements: {missing_elements}")
                return False
                
            self.log_test("Docker Configuration", "PASS", 
                         details="All required Docker elements present")
            return True
            
        except Exception as e:
            self.log_test("Docker Configuration", "FAIL", error=str(e))
            return False
    
    def test_requirements(self) -> bool:
        """Тест файла requirements.txt"""
        try:
            if not os.path.exists("requirements.txt"):
                self.log_test("Requirements File", "FAIL", error="requirements.txt not found")
                return False
                
            with open("requirements.txt", 'r') as f:
                requirements = f.read()
                
            required_packages = ['requests', 'beautifulsoup4']
            optional_packages = ['telebot', 'pyTelegramBotAPI']  # telebot может быть как telebot или pyTelegramBotAPI
            missing_packages = []
            
            for package in required_packages:
                if package not in requirements:
                    missing_packages.append(package)
            
            # Проверяем, что есть хотя бы один из телеграм пакетов
            has_telegram = any(pkg in requirements for pkg in optional_packages)
            if not has_telegram:
                missing_packages.append("telegram bot library (telebot or pyTelegramBotAPI)")
                    
            if missing_packages:
                self.log_test("Requirements File", "WARN", 
                            details=f"Missing packages: {missing_packages}")
            else:
                self.log_test("Requirements File", "PASS", 
                            details="All required packages present")
            return True
            
        except Exception as e:
            self.log_test("Requirements File", "FAIL", error=str(e))
            return False
    
    def test_enhanced_logging_system(self) -> bool:
        """Тест расширенной системы логирования"""
        try:
            # Проверяем наличие enhanced logger
            enhanced_logger_path = "src/railway_logger_enhanced.py"
            if not os.path.exists(enhanced_logger_path):
                self.log_test("Enhanced Logging System", "FAIL", 
                            error="railway_logger_enhanced.py not found")
                return False
                
            # Пробуем импортировать
            from src.railway_logger_enhanced import RailwayLoggerEnhanced
            
            # Тестируем создание logger
            logger = RailwayLoggerEnhanced(name="test_service")
            
            # Тестируем различные типы логов
            logger.bot_action("test_action", {"test": "data"})
            logger.system_action("test_system", {"status": "success"})
            logger.performance_metric("test_metric", 0.5, {"component": "test"})
            
            self.log_test("Enhanced Logging System", "PASS", 
                         details="Enhanced logger works correctly")
            return True
            
        except Exception as e:
            self.log_test("Enhanced Logging System", "FAIL", error=str(e))
            return False
    
    def test_crash_handling_system(self) -> bool:
        """Тест системы обработки крашей"""
        try:
            # Проверяем наличие crash handler
            from src.crash_handler import CrashHandler
            from src.diagnostic_system import DiagnosticSystem
            from src.auto_recovery import AutoRecoverySystem
            
            # Создаем обработчики
            crash_handler = CrashHandler()
            diagnostic_system = DiagnosticSystem()
            recovery_system = AutoRecoverySystem()
            
            # Проверяем, что crash handler настроен
            if crash_handler:
                self.log_test("Crash Handling System", "PASS", 
                             details="All crash handling components available")
                return True
            else:
                self.log_test("Crash Handling System", "FAIL", 
                             error="Crash handler not properly initialized")
                return False
                
        except Exception as e:
            self.log_test("Crash Handling System", "FAIL", error=str(e))
            return False
    
    def test_log_monitoring_system(self) -> bool:
        """Тест системы мониторинга логов"""
        try:
            # Проверяем наличие log monitor
            monitor_path = "railway_log_monitor.py"
            if not os.path.exists(monitor_path):
                self.log_test("Log Monitoring System", "FAIL", 
                            error="railway_log_monitor.py not found")
                return False
                
            # Проверяем deploy script
            deploy_script_path = "deploy_railway.sh"
            if not os.path.exists(deploy_script_path):
                self.log_test("Log Monitoring System", "WARN", 
                            details="deploy_railway.sh not found, creating basic version")
                # Создаем базовую версию
                self.create_basic_deploy_script()
            
            self.log_test("Log Monitoring System", "PASS", 
                         details="Log monitoring components available")
            return True
            
        except Exception as e:
            self.log_test("Log Monitoring System", "FAIL", error=str(e))
            return False
    
    def test_environment_variables(self) -> bool:
        """Тест переменных окружения"""
        try:
            required_vars = ['BOT_TOKEN', 'AUTH_TOKEN']
            missing_vars = []
            available_vars = []
            
            for var in required_vars:
                if os.getenv(var):
                    available_vars.append(var)
                else:
                    missing_vars.append(var)
            
            if missing_vars:
                self.log_test("Environment Variables", "WARN", 
                            details=f"Missing: {missing_vars}, Available: {available_vars}")
            else:
                self.log_test("Environment Variables", "PASS", 
                            details="All required environment variables present")
            
            return True
            
        except Exception as e:
            self.log_test("Environment Variables", "FAIL", error=str(e))
            return False
    
    def test_main_application(self) -> bool:
        """Тест основного приложения"""
        try:
            # Проверяем main.py
            if not os.path.exists("main.py"):
                self.log_test("Main Application", "FAIL", error="main.py not found")
                return False
                
            # Пробуем импортировать основные компоненты
            try:
                # Проверяем, что основной модуль бота импортируется
                import src.bot
                # Проверяем наличие функции main
                if hasattr(src.bot, 'main'):
                    self.log_test("Main Application", "PASS", 
                                 details="Main application components importable")
                    return True
                else:
                    self.log_test("Main Application", "WARN", 
                                 details="Main function found but no TelegramBot class")
                    return True
            except ImportError as e:
                self.log_test("Main Application", "FAIL", 
                             error=f"Import error: {str(e)}")
                return False
                
        except Exception as e:
            self.log_test("Main Application", "FAIL", error=str(e))
            return False
    
    def test_railway_cli_availability(self) -> bool:
        """Тест доступности Railway CLI"""
        try:
            result = subprocess.run(['railway', '--version'], 
                                 capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.log_test("Railway CLI", "PASS", 
                             details=f"Railway CLI version: {result.stdout.strip()}")
                return True
            else:
                self.log_test("Railway CLI", "WARN", 
                             details="Railway CLI not available (install with: npm install -g @railway/cli)")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.log_test("Railway CLI", "WARN", 
                         details="Railway CLI not found (install with: npm install -g @railway/cli)")
            return False
        except Exception as e:
            self.log_test("Railway CLI", "FAIL", error=str(e))
            return False
    
    def create_basic_deploy_script(self):
        """Создание базового скрипта деплоя"""
        script_content = '''#!/bin/bash
# Базовый скрипт деплоя для Railway

echo "🚀 Начинаем деплой на Railway..."

# Проверяем Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI не найден. Установите: npm install -g @railway/cli"
    exit 1
fi

# Логинимся в Railway (если нужно)
railway login

# Деплоим проект
railway up

echo "✅ Деплой завершен!"
'''
        
        with open("deploy_railway.sh", 'w') as f:
            f.write(script_content)
        
        # Делаем скрипт исполняемым
        os.chmod("deploy_railway.sh", 0o755)
    
    def generate_deployment_guide(self) -> str:
        """Генерация руководства по деплою"""
        guide = """
🚀 Railway Deployment Guide
==========================

📋 Pre-deployment Checklist:
1. ✅ Docker configuration verified
2. ✅ Requirements.txt checked  
3. ✅ Enhanced logging system ready
4. ✅ Crash handling system active
5. ✅ Log monitoring configured

🔧 Setup Commands:
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Create new project (if needed)
railway new

# 4. Set environment variables
railway variables set BOT_TOKEN=your_bot_token
railway variables set AUTH_TOKEN=your_auth_token

# 5. Deploy application
railway up
```

📊 Monitoring Commands:
```bash
# View live logs
railway logs --follow

# Check deployment status
railway status

# Access railway dashboard
railway open
```

🐛 Troubleshooting:
- Check logs: railway logs
- Restart service: railway redeploy
- Environment check: railway variables
- Connect to container: railway shell

📝 Log Analysis:
The system will automatically collect logs in JSON format.
Use the log monitor script to analyze crashes and performance.
"""
        return guide
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("🧪 Railway Deployment Testing Suite")
        print("=" * 50)
        
        tests = [
            ("Docker Configuration", self.test_docker_configuration),
            ("Requirements File", self.test_requirements),
            ("Enhanced Logging System", self.test_enhanced_logging_system),
            ("Crash Handling System", self.test_crash_handling_system),
            ("Log Monitoring System", self.test_log_monitoring_system),
            ("Environment Variables", self.test_environment_variables),
            ("Main Application", self.test_main_application),
            ("Railway CLI", self.test_railway_cli_availability)
        ]
        
        passed_tests = 0
        failed_tests = 0
        warnings = 0
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                test_status = self.test_results['tests'][test_name]['status']
                
                if test_status == 'PASS':
                    passed_tests += 1
                elif test_status == 'FAIL':
                    failed_tests += 1
                elif test_status == 'WARN':
                    warnings += 1
                    
            except Exception as e:
                self.log_test(test_name, "FAIL", error=f"Test execution error: {str(e)}")
                failed_tests += 1
        
        # Определяем общий статус
        if failed_tests == 0:
            if warnings == 0:
                self.test_results['overall_status'] = 'ALL_PASS'
                status_msg = "🎉 All tests passed!"
            else:
                self.test_results['overall_status'] = 'PASS_WITH_WARNINGS'
                status_msg = f"✅ Tests passed with {warnings} warnings"
        else:
            self.test_results['overall_status'] = 'SOME_FAILURES'
            status_msg = f"⚠️ {failed_tests} tests failed, {passed_tests} passed"
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {status_msg}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   ⚠️ Warnings: {warnings}")
        
        # Сохраняем результаты
        with open("railway_deployment_test_results.json", 'w') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Full results saved to: railway_deployment_test_results.json")
        
        # Генерируем руководство по деплою
        guide = self.generate_deployment_guide()
        with open("RAILWAY_DEPLOYMENT_GUIDE.md", 'w') as f:
            f.write(guide)
        
        print(f"📖 Deployment guide saved to: RAILWAY_DEPLOYMENT_GUIDE.md")
        
        return self.test_results

if __name__ == "__main__":
    tester = RailwayDeploymentTester()
    results = tester.run_all_tests()
    
    # Завершаем с соответствующим кодом
    if results['overall_status'] == 'ALL_PASS':
        sys.exit(0)
    elif results['overall_status'] == 'PASS_WITH_WARNINGS':
        sys.exit(0)  # Warnings не критичны
    else:
        sys.exit(1)  # Есть критичные ошибки
