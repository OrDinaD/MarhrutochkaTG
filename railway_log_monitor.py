#!/usr/bin/env python3
"""
Система мониторинга и анализа логов Railway
Автоматическое обнаружение проблем и crash событий
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

class RailwayLogMonitor:
    """Монитор логов Railway с автоматическим анализом"""
    
    def __init__(self):
        self.is_monitoring = False
        self.alert_patterns = {
            "crash": [
                r"CRASH|💥|CRITICAL|FATAL",
                r"Exception|Error|Failed",
                r"Process exited|Container crashed"
            ],
            "warning": [
                r"WARNING|WARN|⚠️",
                r"Timeout|Slow response",
                r"Memory usage high|CPU usage high"
            ],
            "recovery": [
                r"🔧|Recovery|Восстановление",
                r"Auto-recovery|Crash handler",
                r"System restored"
            ],
            "performance": [
                r"📊|Metric|Performance",
                r"Response time|Memory usage",
                r"CPU usage|Network latency"
            ]
        }
        
        self.crash_keywords = [
            "crash", "exception", "error", "failed", "critical", "fatal",
            "💥", "❌", "🚨", "traceback", "segfault", "abort"
        ]
        
        self.stats = {
            "total_logs": 0,
            "crash_events": 0,
            "warning_events": 0,
            "recovery_events": 0,
            "last_crash_time": None,
            "uptime_start": datetime.now()
        }
    
    def parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Парсит строку лога"""
        try:
            # Пытаемся распарсить как JSON
            log_data = json.loads(line)
            return log_data
        except json.JSONDecodeError:
            # Если не JSON, создаем базовую структуру
            return {
                "timestamp": datetime.now().isoformat(),
                "level": "info",
                "message": line.strip(),
                "raw": True
            }
    
    def analyze_log(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует лог на предмет проблем"""
        analysis = {
            "category": "normal",
            "severity": "info",
            "alerts": [],
            "recommendations": []
        }
        
        message = log_data.get("message", "").lower()
        level = log_data.get("level", "info").lower()
        
        # Анализ на crash события
        if any(keyword in message for keyword in self.crash_keywords) or level in ["critical", "error"]:
            analysis["category"] = "crash"
            analysis["severity"] = "critical"
            analysis["alerts"].append("🚨 Обнаружено crash событие")
            analysis["recommendations"].append("Проверьте crash handler логи")
            analysis["recommendations"].append("Запустите диагностику системы")
            self.stats["crash_events"] += 1
            self.stats["last_crash_time"] = datetime.now()
        
        # Анализ на предупреждения
        elif level == "warning" or any(re.search(pattern, message, re.IGNORECASE) for pattern in self.alert_patterns["warning"]):
            analysis["category"] = "warning"
            analysis["severity"] = "warning"
            analysis["alerts"].append("⚠️ Обнаружено предупреждение")
            self.stats["warning_events"] += 1
        
        # Анализ recovery событий
        elif any(re.search(pattern, message, re.IGNORECASE) for pattern in self.alert_patterns["recovery"]):
            analysis["category"] = "recovery"
            analysis["severity"] = "info"
            analysis["alerts"].append("🔧 Событие автовосстановления")
            self.stats["recovery_events"] += 1
        
        # Анализ метрик производительности
        elif any(re.search(pattern, message, re.IGNORECASE) for pattern in self.alert_patterns["performance"]):
            analysis["category"] = "performance"
            analysis["severity"] = "info"
            
            # Проверяем на медленные операции
            if "slow" in message or "timeout" in message:
                analysis["alerts"].append("🐌 Медленная операция")
                analysis["recommendations"].append("Оптимизируйте производительность")
        
        return analysis
    
    def format_alert(self, log_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Форматирует алерт для вывода"""
        timestamp = log_data.get("timestamp", datetime.now().isoformat())
        message = log_data.get("message", "")
        
        # Определяем цвет по серьезности
        if analysis["severity"] == "critical":
            color = "\033[0;31m"  # Красный
            icon = "🚨"
        elif analysis["severity"] == "warning":
            color = "\033[1;33m"  # Желтый
            icon = "⚠️"
        elif analysis["category"] == "recovery":
            color = "\033[0;32m"  # Зеленый
            icon = "🔧"
        else:
            color = "\033[0;34m"  # Синий
            icon = "📊"
        
        reset = "\033[0m"
        
        alert_text = f"{color}{icon} [{timestamp[:19]}] {message[:100]}{reset}"
        
        if analysis["alerts"]:
            for alert in analysis["alerts"]:
                alert_text += f"\n  {color}├─ {alert}{reset}"
        
        if analysis["recommendations"]:
            for rec in analysis["recommendations"]:
                alert_text += f"\n  {color}└─ 💡 {rec}{reset}"
        
        return alert_text
    
    def get_stats_summary(self) -> str:
        """Возвращает сводку статистики"""
        uptime = datetime.now() - self.stats["uptime_start"]
        
        return f"""
📊 Статистика мониторинга логов:
═══════════════════════════════
⏱️  Время работы: {str(uptime).split('.')[0]}
📝 Всего логов: {self.stats['total_logs']}
💥 Crash события: {self.stats['crash_events']}
⚠️  Предупреждения: {self.stats['warning_events']}
🔧 События восстановления: {self.stats['recovery_events']}
🕐 Последний краш: {self.stats['last_crash_time'].strftime('%H:%M:%S') if self.stats['last_crash_time'] else 'Нет'}
"""
    
    async def monitor_railway_logs(self, follow: bool = True, filter_crashes: bool = False):
        """Мониторит логи Railway в реальном времени"""
        print("🔍 Запуск мониторинга Railway логов...")
        print("💡 Нажмите Ctrl+C для выхода")
        print("=" * 50)
        
        self.is_monitoring = True
        
        try:
            # Формируем команду для railway logs
            cmd = ["railway", "logs"]
            if follow:
                cmd.append("--follow")
            if filter_crashes:
                cmd.extend(["--filter", "@level:error OR @level:critical"])
            
            # Запускаем процесс мониторинга
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Читаем логи в реальном времени
            while self.is_monitoring and process.poll() is None:
                line = process.stdout.readline()
                if line:
                    self.stats["total_logs"] += 1
                    
                    # Парсим и анализируем лог
                    log_data = self.parse_log_line(line)
                    if log_data:
                        analysis = self.analyze_log(log_data)
                        
                        # Выводим важные события
                        if analysis["category"] in ["crash", "warning", "recovery"] or not filter_crashes:
                            alert = self.format_alert(log_data, analysis)
                            print(alert)
                        
                        # Периодически выводим статистику
                        if self.stats["total_logs"] % 100 == 0:
                            print(f"\n{self.get_stats_summary()}")
                
                await asyncio.sleep(0.1)  # Небольшая пауза
        
        except KeyboardInterrupt:
            print("\n\n🛑 Мониторинг остановлен пользователем")
        except Exception as e:
            print(f"\n❌ Ошибка мониторинга: {e}")
        finally:
            self.is_monitoring = False
            if 'process' in locals():
                process.terminate()
            
            print(f"\n{self.get_stats_summary()}")
    
    def search_logs(self, query: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Поиск в логах за указанный период"""
        print(f"🔍 Поиск логов: '{query}' за последние {hours} часов")
        
        try:
            # Получаем логи за период
            cmd = ["railway", "logs", "--json", "--since", f"{hours}h"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Ошибка получения логов: {result.stderr}")
                return []
            
            # Парсим логи
            logs = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        log_data = json.loads(line)
                        if query.lower() in log_data.get("message", "").lower():
                            logs.append(log_data)
                    except json.JSONDecodeError:
                        continue
            
            print(f"✅ Найдено {len(logs)} логов")
            return logs
        
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return []
    
    def analyze_crash_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """Анализирует паттерны крашей"""
        print(f"🔬 Анализ паттернов крашей за {hours} часов...")
        
        crash_logs = []
        for keyword in self.crash_keywords:
            logs = self.search_logs(keyword, hours)
            crash_logs.extend(logs)
        
        # Убираем дубликаты
        unique_crashes = {log.get("timestamp", ""): log for log in crash_logs}
        crash_logs = list(unique_crashes.values())
        
        if not crash_logs:
            print("✅ Крашей не обнаружено")
            return {"crashes": [], "patterns": {}, "recommendations": []}
        
        # Анализируем паттерны
        patterns = {
            "by_hour": {},
            "by_type": {},
            "by_message": {}
        }
        
        for log in crash_logs:
            # По времени
            timestamp = log.get("timestamp", "")
            if timestamp:
                hour = timestamp[:13]  # YYYY-MM-DDTHH
                patterns["by_hour"][hour] = patterns["by_hour"].get(hour, 0) + 1
            
            # По типу
            level = log.get("level", "unknown")
            patterns["by_type"][level] = patterns["by_type"].get(level, 0) + 1
            
            # По сообщению
            message = log.get("message", "")[:50]
            patterns["by_message"][message] = patterns["by_message"].get(message, 0) + 1
        
        # Генерируем рекомендации
        recommendations = []
        
        if len(crash_logs) > 10:
            recommendations.append("🚨 Высокая частота крашей - требуется немедленное внимание")
        
        if patterns["by_type"].get("critical", 0) > 0:
            recommendations.append("💀 Обнаружены критичные ошибки - проверьте системные ресурсы")
        
        most_common_hour = max(patterns["by_hour"], key=patterns["by_hour"].get) if patterns["by_hour"] else None
        if most_common_hour:
            recommendations.append(f"📅 Пик крашей в {most_common_hour} - проверьте нагрузку в это время")
        
        analysis = {
            "crashes": crash_logs,
            "patterns": patterns,
            "recommendations": recommendations,
            "total_crashes": len(crash_logs),
            "crash_rate": len(crash_logs) / hours
        }
        
        print(f"💥 Всего крашей: {len(crash_logs)}")
        print(f"📊 Частота: {analysis['crash_rate']:.2f} крашей/час")
        
        for rec in recommendations:
            print(f"💡 {rec}")
        
        return analysis

async def main():
    """Главная функция для CLI использования"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Railway Log Monitor")
    parser.add_argument("--monitor", action="store_true", help="Мониторинг логов в реальном времени")
    parser.add_argument("--crashes-only", action="store_true", help="Показывать только краши")
    parser.add_argument("--search", type=str, help="Поиск в логах")
    parser.add_argument("--analyze", action="store_true", help="Анализ паттернов крашей")
    parser.add_argument("--hours", type=int, default=24, help="Период анализа в часах")
    
    args = parser.parse_args()
    
    monitor = RailwayLogMonitor()
    
    if args.monitor:
        await monitor.monitor_railway_logs(follow=True, filter_crashes=args.crashes_only)
    elif args.search:
        logs = monitor.search_logs(args.search, args.hours)
        for log in logs[:10]:  # Показываем первые 10
            print(json.dumps(log, indent=2, ensure_ascii=False))
    elif args.analyze:
        monitor.analyze_crash_patterns(args.hours)
    else:
        print("Используйте --help для списка команд")

if __name__ == "__main__":
    asyncio.run(main())
