#!/usr/bin/env python3
"""
Система диагностики и восстановления
Анализирует крэш-репорты и предлагает решения
"""

import os
import json
import re
import asyncio
import platform
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from .railway_logger_enhanced import railway_logger

class DiagnosticSystem:
    """Система автоматической диагностики проблем"""
    
    def __init__(self):
        self.crash_logs_dir = Path('crash_logs')
        self.solutions_db = self._load_solutions_database()
        
    def _load_solutions_database(self) -> Dict[str, Any]:
        """Загружает базу знаний с решениями типичных проблем"""
        return {
            "telegram.error.NetworkError": {
                "category": "network",
                "severity": "high",
                "description": "Проблемы с сетевым подключением к Telegram API",
                "solutions": [
                    "Проверить интернет-соединение Railway",
                    "Проверить статус Telegram API (https://status.telegram.org/)",
                    "Увеличить timeout в настройках бота",
                    "Добавить retry механизм для сетевых запросов"
                ],
                "prevention": [
                    "Настроить health checks",
                    "Добавить circuit breaker pattern",
                    "Использовать exponential backoff"
                ]
            },
            "telegram.error.Conflict": {
                "category": "configuration",
                "severity": "critical",
                "description": "Бот уже запущен в другом месте",
                "solutions": [
                    "Остановить все другие экземпляры бота",
                    "Проверить активные деплои в Railway",
                    "Убедиться что используется правильный токен",
                    "Добавить проверку активности бота перед запуском"
                ],
                "prevention": [
                    "Использовать уникальные токены для разных окружений",
                    "Добавить graceful shutdown",
                    "Настроить проверку конфликтов при старте"
                ]
            },
            "requests.exceptions.ConnectionError": {
                "category": "network",
                "severity": "high", 
                "description": "Ошибка подключения к внешним API",
                "solutions": [
                    "Проверить доступность marshrutochka.ru",
                    "Проверить DNS разрешение",
                    "Увеличить timeout для запросов",
                    "Добавить fallback механизм"
                ],
                "prevention": [
                    "Мониторинг доступности внешних сервисов",
                    "Кеширование данных",
                    "Использование нескольких источников данных"
                ]
            },
            "ModuleNotFoundError": {
                "category": "dependencies",
                "severity": "critical",
                "description": "Отсутствует необходимый модуль",
                "solutions": [
                    "Проверить requirements.txt",
                    "Переустановить зависимости",
                    "Проверить версии пакетов",
                    "Очистить pip cache и переустановить"
                ],
                "prevention": [
                    "Зафиксировать версии в requirements.txt",
                    "Использовать pip freeze",
                    "Регулярно обновлять зависимости"
                ]
            },
            "FileNotFoundError": {
                "category": "filesystem",
                "severity": "medium",
                "description": "Отсутствует необходимый файл",
                "solutions": [
                    "Проверить структуру проекта",
                    "Создать отсутствующие директории",
                    "Проверить права доступа к файлам",
                    "Убедиться что файлы не игнорируются в .gitignore"
                ],
                "prevention": [
                    "Создавать директории при инициализации",
                    "Добавить проверки существования файлов",
                    "Использовать pathlib для работы с путями"
                ]
            },
            "json.JSONDecodeError": {
                "category": "data",
                "severity": "medium",
                "description": "Ошибка парсинга JSON данных",
                "solutions": [
                    "Проверить валидность JSON файлов",
                    "Восстановить поврежденные файлы из бэкапа",
                    "Очистить кэш и пересоздать файлы",
                    "Добавить валидацию JSON при записи"
                ],
                "prevention": [
                    "Атомарная запись файлов",
                    "Валидация перед сохранением",
                    "Создание бэкапов критичных файлов"
                ]
            },
            "MemoryError": {
                "category": "resources",
                "severity": "critical",
                "description": "Недостаточно памяти для выполнения операции",
                "solutions": [
                    "Увеличить лимиты памяти в Railway",
                    "Оптимизировать использование памяти",
                    "Добавить garbage collection",
                    "Разбить большие операции на части"
                ],
                "prevention": [
                    "Мониторинг использования памяти",
                    "Профилирование приложения",
                    "Использование генераторов вместо списков"
                ]
            }
        }
    
    def analyze_crash(self, crash_data: Dict[str, Any]) -> Dict[str, Any]:
        """Синхронный метод анализа краша (для обратной совместимости)"""
        error_type = crash_data.get('error_type', 'Unknown')
        
        # Ищем известное решение
        solution = self.solutions_db.get(error_type, {
            "category": "unknown",
            "severity": "medium",
            "description": "Unknown error type",
            "solutions": ["Check logs for more details"],
            "prevention": []
        })
        
        return {
            "category": solution.get('category', 'unknown'),
            "severity": solution.get('severity', 'medium'),
            "solutions": solution.get('solutions', []),
            "prevention": solution.get('prevention', []),
            "description": solution.get('description', '')
        }
    
    async def analyze_crash_report_from_exception(self, exception: Exception) -> Optional[Dict[str, Any]]:
        """Создает и анализирует crash report из исключения"""
        try:
            # Создаем мини crash report
            crash_report = {
                "crash_id": f"test_{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "exception": {
                    "type": type(exception).__name__,
                    "message": str(exception),
                    "traceback": traceback.format_exc()
                },
                "system_info": {
                    "platform": platform.system(),
                    "python_version": platform.python_version()
                }
            }
            
            # Анализируем
            return await self.analyze_crash_report(crash_report)
            
        except Exception as e:
            railway_logger.error(f"Failed to analyze exception: {e}", exc_info=True)
            return None

    async def analyze_crash_report(self, crash_report: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует краш-репорт и предлагает решения"""
        crash_id = crash_report.get('crash_id', 'unknown')
        crash_file = self.crash_logs_dir / f"{crash_id}.json"
        
        # Анализируем переданный crash_report напрямую, не загружаем из файла
        analysis_result = {
            "crash_id": crash_id,
            "timestamp": datetime.now().isoformat(),
            "analysis": {}
        }
        
        try:
            # Используем переданный crash_report
            crash_data = crash_report
            
            analysis = {
                "crash_id": crash_id,
                "timestamp": crash_data.get('timestamp'),
                "primary_issue": self._analyze_primary_issue(crash_data),
                "system_health": self._analyze_system_health(crash_data),
                "dependency_issues": self._analyze_dependencies(crash_data),
                "network_issues": self._analyze_network(crash_data),
                "resource_issues": self._analyze_resources(crash_data),
                "recommendations": self._generate_recommendations(crash_data),
                "recovery_plan": self._generate_recovery_plan(crash_data)
            }
            
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze crash report: {e}"}
    
    def _analyze_primary_issue(self, crash_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует основную проблему"""
        exception = crash_data.get('exception', {})
        exception_type = exception.get('type', 'Unknown')
        exception_message = exception.get('message', '')
        traceback_lines = exception.get('traceback_lines', [])
        
        # Ищем известное решение
        solution = self.solutions_db.get(exception_type, {})
        
        # Анализируем трейсбек для дополнительной информации
        traceback_analysis = self._analyze_traceback(traceback_lines)
        
        return {
            "exception_type": exception_type,
            "exception_message": exception_message,
            "known_solution": solution,
            "traceback_analysis": traceback_analysis,
            "severity": solution.get('severity', 'unknown'),
            "category": solution.get('category', 'unknown')
        }
    
    def _analyze_traceback(self, traceback_lines: List[str]) -> Dict[str, Any]:
        """Анализирует трейсбек для получения дополнительной информации"""
        analysis = {
            "files_involved": [],
            "functions_involved": [],
            "line_numbers": [],
            "patterns": []
        }
        
        for line in traceback_lines:
            # Извлекаем файлы
            file_match = re.search(r'File "([^"]+)"', line)
            if file_match:
                file_path = file_match.group(1)
                if not file_path.startswith('/opt/homebrew') and not file_path.startswith('/usr'):
                    analysis["files_involved"].append(file_path)
            
            # Извлекаем функции
            func_match = re.search(r'in (\w+)', line)
            if func_match:
                analysis["functions_involved"].append(func_match.group(1))
            
            # Извлекаем номера строк
            line_match = re.search(r'line (\d+)', line)
            if line_match:
                analysis["line_numbers"].append(int(line_match.group(1)))
            
            # Ищем специфичные паттерны
            if 'rate limit' in line.lower():
                analysis["patterns"].append("rate_limiting")
            elif 'timeout' in line.lower():
                analysis["patterns"].append("timeout")
            elif 'permission' in line.lower():
                analysis["patterns"].append("permissions")
            elif 'token' in line.lower() and 'invalid' in line.lower():
                analysis["patterns"].append("invalid_token")
        
        return analysis
    
    def _analyze_system_health(self, crash_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует состояние системы"""
        system_info = crash_data.get('system_info', {})
        resources = system_info.get('resources', {})
        environment = system_info.get('environment', {})
        
        health_score = 100
        issues = []
        
        # Проверяем использование ресурсов
        if isinstance(resources.get('cpu_percent'), (int, float)):
            cpu_usage = resources['cpu_percent']
            if cpu_usage > 90:
                health_score -= 20
                issues.append(f"High CPU usage: {cpu_usage}%")
            elif cpu_usage > 70:
                health_score -= 10
                issues.append(f"Elevated CPU usage: {cpu_usage}%")
        
        memory = resources.get('memory', {})
        if isinstance(memory.get('percent'), (int, float)):
            memory_usage = memory['percent']
            if memory_usage > 90:
                health_score -= 30
                issues.append(f"High memory usage: {memory_usage}%")
            elif memory_usage > 70:
                health_score -= 15
                issues.append(f"Elevated memory usage: {memory_usage}%")
        
        disk = resources.get('disk', {})
        if isinstance(disk.get('percent'), (int, float)):
            disk_usage = disk['percent']
            if disk_usage > 95:
                health_score -= 25
                issues.append(f"Critical disk usage: {disk_usage}%")
            elif disk_usage > 80:
                health_score -= 10
                issues.append(f"High disk usage: {disk_usage}%")
        
        # Проверяем окружение
        if not environment.get('railway_service'):
            health_score -= 5
            issues.append("Not running in Railway environment")
        
        return {
            "health_score": max(0, health_score),
            "issues": issues,
            "resource_status": {
                "cpu": resources.get('cpu_percent', 'unknown'),
                "memory": memory.get('percent', 'unknown'),
                "disk": disk.get('percent', 'unknown')
            }
        }
    
    def _analyze_dependencies(self, crash_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует проблемы с зависимостями"""
        dependencies = crash_data.get('dependencies', {})
        issues = []
        
        if 'error' in dependencies:
            issues.append(f"Failed to collect dependencies: {dependencies['error']}")
        
        # Проверяем наличие requirements.txt
        requirements = dependencies.get('requirements_file')
        if not requirements:
            issues.append("Missing requirements.txt file")
        
        # Проверяем установленные пакеты
        packages = dependencies.get('installed_packages', [])
        if not packages:
            issues.append("No installed packages found")
        
        # Ищем потенциальные конфликты версий
        critical_packages = ['python-telegram-bot', 'requests', 'beautifulsoup4', 'lxml']
        missing_packages = []
        
        package_names = [pkg.get('name', '').lower() for pkg in packages if isinstance(pkg, dict)]
        
        for critical_pkg in critical_packages:
            if critical_pkg not in package_names:
                missing_packages.append(critical_pkg)
        
        if missing_packages:
            issues.append(f"Missing critical packages: {', '.join(missing_packages)}")
        
        return {
            "issues": issues,
            "packages_count": len(packages),
            "missing_critical": missing_packages,
            "has_requirements": bool(requirements)
        }
    
    def _analyze_network(self, crash_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует сетевые проблемы"""
        network_info = crash_data.get('network_info', {})
        issues = []
        connectivity_score = 100
        
        if 'error' in network_info:
            issues.append(f"Failed to collect network info: {network_info['error']}")
            return {"issues": issues, "connectivity_score": 0}
        
        # Проверяем внешнюю связность
        external_connectivity = network_info.get('external_connectivity', {})
        
        for url, status in external_connectivity.items():
            if not status.get('accessible', False):
                connectivity_score -= 30
                error = status.get('error', 'Unknown error')
                issues.append(f"Cannot reach {url}: {error}")
            elif status.get('response_time', 0) > 10:
                connectivity_score -= 10
                issues.append(f"Slow response from {url}: {status['response_time']:.2f}s")
        
        # Проверяем количество соединений
        connections = network_info.get('connections', [])
        if len(connections) > 100:
            connectivity_score -= 10
            issues.append(f"High number of connections: {len(connections)}")
        
        return {
            "issues": issues,
            "connectivity_score": max(0, connectivity_score),
            "external_services": external_connectivity,
            "connections_count": len(connections)
        }
    
    def _analyze_resources(self, crash_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует проблемы с ресурсами"""
        system_info = crash_data.get('system_info', {})
        resources = system_info.get('resources', {})
        issues = []
        
        # Анализируем память
        memory = resources.get('memory', {})
        if isinstance(memory.get('available'), int):
            available_mb = memory['available'] / (1024 * 1024)
            if available_mb < 100:
                issues.append(f"Low available memory: {available_mb:.1f}MB")
            
            total_mb = memory.get('total', 0) / (1024 * 1024)
            if total_mb < 500:
                issues.append(f"Low total memory: {total_mb:.1f}MB")
        
        # Анализируем диск
        disk = resources.get('disk', {})
        if isinstance(disk.get('free'), int):
            free_mb = disk['free'] / (1024 * 1024)
            if free_mb < 100:
                issues.append(f"Low disk space: {free_mb:.1f}MB")
        
        # Анализируем CPU
        cpu_count = resources.get('cpu_count', 0)
        if cpu_count < 1:
            issues.append("Low CPU count")
        
        return {
            "issues": issues,
            "memory_mb": {
                "total": memory.get('total', 0) / (1024 * 1024) if memory.get('total') else 0,
                "available": memory.get('available', 0) / (1024 * 1024) if memory.get('available') else 0
            },
            "disk_mb": {
                "total": disk.get('total', 0) / (1024 * 1024) if disk.get('total') else 0,
                "free": disk.get('free', 0) / (1024 * 1024) if disk.get('free') else 0
            },
            "cpu_count": cpu_count
        }
    
    def _generate_recommendations(self, crash_data: Dict[str, Any]) -> List[str]:
        """Генерирует рекомендации по исправлению"""
        recommendations = []
        
        # Получаем основную проблему
        exception = crash_data.get('exception', {})
        exception_type = exception.get('type', '')
        
        # Добавляем специфичные рекомендации
        if exception_type in self.solutions_db:
            solution = self.solutions_db[exception_type]
            recommendations.extend(solution.get('solutions', []))
        
        # Добавляем общие рекомендации на основе анализа
        system_health = self._analyze_system_health(crash_data)
        if system_health['health_score'] < 70:
            recommendations.append("Оптимизировать использование ресурсов")
        
        network_analysis = self._analyze_network(crash_data)
        if network_analysis['connectivity_score'] < 70:
            recommendations.append("Проверить и исправить сетевые проблемы")
        
        dependency_analysis = self._analyze_dependencies(crash_data)
        if dependency_analysis['missing_critical']:
            recommendations.append("Установить отсутствующие критичные пакеты")
        
        # Добавляем временные рекомендации
        recommendations.extend([
            "Перезапустить сервис в Railway",
            "Проверить статус внешних сервисов",
            "Очистить кэш и временные файлы",
            "Проверить актуальность токенов и ключей API"
        ])
        
        return list(set(recommendations))  # Убираем дубликаты
    
    def _generate_recovery_plan(self, crash_data: Dict[str, Any]) -> Dict[str, Any]:
        """Генерирует план восстановления"""
        exception = crash_data.get('exception', {})
        exception_type = exception.get('type', '')
        
        # Базовый план восстановления
        plan = {
            "immediate_actions": [
                "Зафиксировать состояние системы",
                "Проверить логи Railway",
                "Перезапустить сервис"
            ],
            "investigation_steps": [
                "Проанализировать последние изменения в коде",
                "Проверить статус внешних API",
                "Сравнить с предыдущими рабочими деплоями"
            ],
            "prevention_measures": [
                "Добавить больше проверок при старте",
                "Улучшить обработку ошибок",
                "Настроить мониторинг"
            ],
            "estimated_time": "15-30 минут"
        }
        
        # Специфичный план для известных проблем
        if exception_type in self.solutions_db:
            solution = self.solutions_db[exception_type]
            plan["prevention_measures"] = solution.get('prevention', plan["prevention_measures"])
            
            if solution.get('severity') == 'critical':
                plan["estimated_time"] = "30-60 минут"
                plan["immediate_actions"].insert(0, "КРИТИЧНО: Немедленное внимание требуется")
        
        return plan
    
    def list_crash_reports(self) -> List[Dict[str, Any]]:
        """Возвращает список всех краш-репортов"""
        reports = []
        
        if not self.crash_logs_dir.exists():
            return reports
        
        for crash_file in self.crash_logs_dir.glob("*.json"):
            try:
                with open(crash_file, 'r', encoding='utf-8') as f:
                    crash_data = json.load(f)
                
                reports.append({
                    "crash_id": crash_data.get('crash_id', crash_file.stem),
                    "timestamp": crash_data.get('timestamp'),
                    "exception_type": crash_data.get('exception', {}).get('type', 'Unknown'),
                    "exception_message": crash_data.get('exception', {}).get('message', '')[:100],
                    "file": str(crash_file)
                })
            except Exception:
                # Пропускаем поврежденные файлы
                continue
        
        # Сортируем по времени (новые первыми)
        reports.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return reports
    
    def get_recent_crashes(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Возвращает краши за последние N часов"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_crashes = []
        for report in self.list_crash_reports():
            try:
                crash_time = datetime.fromisoformat(report['timestamp'].replace('Z', '+00:00'))
                if crash_time > cutoff_time:
                    recent_crashes.append(report)
            except (ValueError, TypeError):
                continue
        
        return recent_crashes

# Глобальный экземпляр
diagnostic_system = DiagnosticSystem()

if __name__ == "__main__":
    # Тест системы диагностики
    print("Testing diagnostic system...")
    
    # Показываем доступные краш-репорты
    reports = diagnostic_system.list_crash_reports()
    print(f"Found {len(reports)} crash reports:")
    
    for report in reports[:5]:  # Показываем первые 5
        print(f"- {report['crash_id']}: {report['exception_type']} at {report['timestamp']}")
    
    # Анализируем последний краш если есть
    if reports:
        latest_crash = reports[0]
        print(f"\nAnalyzing latest crash: {latest_crash['crash_id']}")
        analysis = diagnostic_system.analyze_crash_report(latest_crash['crash_id'])
        print(json.dumps(analysis, indent=2, ensure_ascii=False, default=str))
