#!/usr/bin/env python3
"""
Система автоматического восстановления и самолечения
Выполняет автоматические действия для восстановления после крашей
"""

import os
import sys
import json
import time
import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import aiohttp
import telegram
from .railway_logger_enhanced import railway_logger

class AutoRecoverySystem:
    """Система автоматического восстановления"""
    
    def __init__(self):
        self.recovery_log = []
        self.max_recovery_attempts = 3
        self.recovery_cooldown = 300  # 5 минут
        self.last_recovery_time = None
        
        # Настройки уведомлений
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_chat_id = os.getenv('ADMIN_TELEGRAM_ID')
        
        # Директории для работы
        self.backup_dir = Path('backups')
        self.backup_dir.mkdir(exist_ok=True)
        
        self.temp_dir = Path('temp_recovery')
        self.temp_dir.mkdir(exist_ok=True)
        
        # Регистрируем recovery actions
        self.recovery_actions = {
            "network_issues": self.recover_network_issues,
            "dependency_issues": self.recover_dependency_issues,
            "file_corruption": self.recover_file_corruption,
            "memory_issues": self.recover_memory_issues,
            "permission_issues": self.recover_permission_issues,
            "token_issues": self.recover_token_issues,
            "general_restart": self.recover_general_restart
        }
    
    async def attempt_auto_recovery(self, crash_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Попытка автоматического восстановления"""
        
        # Проверяем cooldown
        if not self._can_attempt_recovery():
            railway_logger.warning("Recovery cooldown active", extra={"cooldown_remaining": self._get_cooldown_remaining()})
            return {
                "attempted": False,
                "reason": "Recovery cooldown active",
                "next_attempt_in": self._get_cooldown_remaining()
            }
        
        recovery_result = {
            "attempted": True,
            "timestamp": datetime.now().isoformat(),
            "crash_id": crash_analysis.get('crash_id'),
            "actions_taken": [],
            "success": False,
            "error": None
        }
        
        try:
            # Определяем стратегию восстановления
            recovery_strategy = self._determine_recovery_strategy(crash_analysis)
            
            await self._notify_recovery_start(crash_analysis, recovery_strategy)
            
            # Выполняем действия по восстановлению
            for action_name in recovery_strategy:
                if action_name in self.recovery_actions:
                    railway_logger.system_action(f"Executing recovery action: {action_name}", data={"crash_id": crash_analysis.get('crash_id')})
                    action_result = await self.recovery_actions[action_name](crash_analysis)
                    recovery_result["actions_taken"].append({
                        "action": action_name,
                        "result": action_result,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    if not action_result.get("success", False):
                        railway_logger.error(f"Recovery action {action_name} failed", extra={"result": action_result})
                        break
            
            # Проверяем успешность восстановления
            recovery_result["success"] = all(
                action["result"].get("success", False) 
                for action in recovery_result["actions_taken"]
            )
            
            # Обновляем время последнего восстановления
            self.last_recovery_time = datetime.now()
            
            await self._notify_recovery_complete(recovery_result)
            
            railway_logger.recovery_event(
                "Auto recovery attempt finished",
                recovery_id=f"rec_{int(time.time())}",
                success=recovery_result["success"],
                data={"crash_id": crash_analysis.get('crash_id'), "actions": len(recovery_result["actions_taken"])}
            )
            
        except Exception as e:
            recovery_result["error"] = str(e)
            recovery_result["success"] = False
            await self._notify_recovery_error(recovery_result, e)
            railway_logger.error(f"Auto recovery failed: {e}", exc_info=True)
        
        # Сохраняем результат
        self.recovery_log.append(recovery_result)
        self._save_recovery_log()
        
        return recovery_result
    
    def _can_attempt_recovery(self) -> bool:
        """Проверяет можно ли выполнять восстановление"""
        if not self.last_recovery_time:
            return True
        
        time_since_last = datetime.now() - self.last_recovery_time
        return time_since_last.total_seconds() > self.recovery_cooldown
    
    def _get_cooldown_remaining(self) -> Optional[int]:
        """Возвращает оставшееся время cooldown в секундах"""
        if not self.last_recovery_time:
            return 0
        
        time_since_last = datetime.now() - self.last_recovery_time
        remaining = self.recovery_cooldown - time_since_last.total_seconds()
        return max(0, int(remaining))
    
    def _determine_recovery_strategy(self, crash_analysis: Dict[str, Any]) -> List[str]:
        """Определяет стратегию восстановления на основе анализа краша"""
        strategy = []
        
        primary_issue = crash_analysis.get('primary_issue', {})
        exception_type = primary_issue.get('exception_type', '')
        category = primary_issue.get('category', '')
        
        # Специфичные стратегии для известных проблем
        if 'NetworkError' in exception_type or 'ConnectionError' in exception_type:
            strategy.extend(['network_issues', 'general_restart'])
        
        elif 'ModuleNotFoundError' in exception_type or 'ImportError' in exception_type:
            strategy.extend(['dependency_issues', 'general_restart'])
        
        elif 'FileNotFoundError' in exception_type or 'PermissionError' in exception_type:
            strategy.extend(['file_corruption', 'permission_issues'])
        
        elif 'MemoryError' in exception_type:
            strategy.extend(['memory_issues', 'general_restart'])
        
        elif 'Conflict' in exception_type:
            strategy.extend(['general_restart'])
        
        elif 'JSONDecodeError' in exception_type:
            strategy.extend(['file_corruption'])
        
        # Стратегии на основе категории
        if category == 'network':
            strategy.append('network_issues')
        elif category == 'dependencies':
            strategy.append('dependency_issues')
        elif category == 'filesystem':
            strategy.extend(['file_corruption', 'permission_issues'])
        elif category == 'resources':
            strategy.append('memory_issues')
        
        # Общие проблемы
        network_issues = crash_analysis.get('network_issues', {})
        if network_issues.get('connectivity_score', 100) < 50:
            strategy.append('network_issues')
        
        dependency_issues = crash_analysis.get('dependency_issues', {})
        if dependency_issues.get('missing_critical'):
            strategy.append('dependency_issues')
        
        # Если ничего специфичного не найдено, используем общий перезапуск
        if not strategy:
            strategy.append('general_restart')
        
        # Убираем дубликаты и ограничиваем количество действий
        strategy = list(dict.fromkeys(strategy))[:3]
        
        return strategy
    
    async def recover_network_issues(self, crash_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Восстановление сетевых проблем"""
        actions = []
        success = True
        
        try:
            # Проверяем связность с критичными сервисами
            critical_urls = [
                "https://api.telegram.org/bot",
                "https://marshrutochka.ru",
                "https://httpbin.org/ip"
            ]
            
            connectivity_results = {}
            async with aiohttp.ClientSession() as session:
                for url in critical_urls:
                    try:
                        start_time = time.time()
                        async with session.get(url, timeout=10) as response:
                            elapsed = time.time() - start_time
                            connectivity_results[url] = {
                                "accessible": True,
                                "status_code": response.status,
                                "response_time": elapsed
                            }
                    except Exception as e:
                        connectivity_results[url] = {
                            "accessible": False,
                            "error": str(e)
                        }
            
            actions.append(f"Connectivity check completed: {connectivity_results}")
            
            # Пытаемся очистить DNS кэш (если возможно)
            try:
                if os.name == 'posix':  # Unix-like systems
                    result = subprocess.run(['sudo', 'systemctl', 'restart', 'systemd-resolved'], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        actions.append("DNS cache cleared successfully")
                    else:
                        actions.append(f"DNS cache clear failed: {result.stderr}")
            except Exception as e:
                actions.append(f"DNS cache clear not possible: {e}")
            
            # Ждем немного для стабилизации сети
            await asyncio.sleep(5)
            actions.append("Network stabilization wait completed")
            
        except Exception as e:
            success = False
            actions.append(f"Network recovery failed: {e}")
        
        return {
            "success": success,
            "actions": actions,
            "connectivity_results": connectivity_results if 'connectivity_results' in locals() else {}
        }
    
    async def recover_dependency_issues(self, crash_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Восстановление проблем с зависимостями"""
        actions = []
        success = True
        
        try:
            # Проверяем requirements.txt
            requirements_file = Path('requirements.txt')
            if requirements_file.exists():
                actions.append("requirements.txt found")
                
                # Переустанавливаем зависимости
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--force-reinstall'
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    actions.append("Dependencies reinstalled successfully")
                else:
                    success = False
                    actions.append(f"Dependency installation failed: {result.stderr}")
            else:
                # Устанавливаем основные зависимости
                critical_packages = [
                    'python-telegram-bot',
                    'requests',
                    'beautifulsoup4',
                    'lxml',
                    'psutil'
                ]
                
                for package in critical_packages:
                    result = subprocess.run([
                        sys.executable, '-m', 'pip', 'install', package
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        actions.append(f"Installed {package}")
                    else:
                        actions.append(f"Failed to install {package}: {result.stderr}")
            
            # Очищаем pip cache
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'cache', 'purge'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                actions.append("Pip cache cleared")
            
        except Exception as e:
            success = False
            actions.append(f"Dependency recovery failed: {e}")
        
        return {
            "success": success,
            "actions": actions
        }
    
    async def recover_file_corruption(self, crash_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Восстановление поврежденных файлов"""
        actions = []
        success = True
        
        try:
            # Создаем бэкап перед восстановлением
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"recovery_backup_{backup_timestamp}"
            
            # Файлы для проверки и восстановления
            critical_files = [
                # 'data/user_sessions.json', - удален, используется memory-only
                'data/monitors.json',
                'data/logs/bot.log'
            ]
            
            for file_path in critical_files:
                path = Path(file_path)
                
                if path.exists():
                    # Проверяем целостность JSON файлов
                    if path.suffix == '.json':
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                json.load(f)
                            actions.append(f"{file_path} is valid")
                        except json.JSONDecodeError:
                            # Файл поврежден, пытаемся восстановить
                            actions.append(f"{file_path} is corrupted, attempting recovery")
                            
                            # Создаем бэкап поврежденного файла
                            backup_file = backup_path / path.name
                            backup_path.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(path, backup_file)
                            
                            # Пытаемся восстановить из пустого JSON
                            if 'sessions' in file_path:
                                path.write_text('{}', encoding='utf-8')
                            elif 'monitors' in file_path:
                                path.write_text('{}', encoding='utf-8')
                            
                            actions.append(f"{file_path} reset to empty state")
                else:
                    # Создаем отсутствующие файлы
                    path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if path.suffix == '.json':
                        path.write_text('{}', encoding='utf-8')
                        actions.append(f"Created missing {file_path}")
                    elif path.suffix == '.log':
                        path.write_text('', encoding='utf-8')
                        actions.append(f"Created missing {file_path}")
            
            # Проверяем директории
            critical_dirs = [
                'logs',
                'crash_logs',
                # 'user_sessions', - удален, используется memory-only
                'src'
            ]
            
            for dir_path in critical_dirs:
                path = Path(dir_path)
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    actions.append(f"Created missing directory {dir_path}")
            
        except Exception as e:
            success = False
            actions.append(f"File recovery failed: {e}")
        
        return {
            "success": success,
            "actions": actions
        }
    
    async def recover_memory_issues(self, crash_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Восстановление проблем с памятью"""
        actions = []
        success = True
        
        try:
            # Принудительная сборка мусора
            import gc
            collected = gc.collect()
            actions.append(f"Garbage collection freed {collected} objects")
            
            # Очищаем кэши если есть
            cache_dirs = [
                '__pycache__',
                '.pytest_cache',
                'temp_recovery'
            ]
            
            for cache_dir in cache_dirs:
                path = Path(cache_dir)
                if path.exists():
                    try:
                        shutil.rmtree(path)
                        actions.append(f"Cleared cache directory {cache_dir}")
                    except Exception as e:
                        actions.append(f"Failed to clear {cache_dir}: {e}")
            
            # Ограничиваем размеры файлов логов
            log_files = Path('logs').glob('*.log') if Path('logs').exists() else []
            for log_file in log_files:
                try:
                    if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                        # Обрезаем файл до последних 1000 строк
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        with open(log_file, 'w', encoding='utf-8') as f:
                            f.writelines(lines[-1000:])
                        
                        actions.append(f"Truncated large log file {log_file}")
                except Exception as e:
                    actions.append(f"Failed to truncate {log_file}: {e}")
            
        except Exception as e:
            success = False
            actions.append(f"Memory recovery failed: {e}")
        
        return {
            "success": success,
            "actions": actions
        }
    
    async def recover_permission_issues(self, crash_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Восстановление проблем с правами доступа"""
        actions = []
        success = True
        
        try:
            # Проверяем и исправляем права на критичные файлы
            critical_paths = [
                'data/logs',
                'data/crash_logs',
                # 'data/user_sessions.json', - удален, используется memory-only
                'data/monitors.json'
            ]
            
            for path_str in critical_paths:
                path = Path(path_str)
                
                if path.exists():
                    try:
                        # Проверяем возможность чтения
                        if path.is_file():
                            with open(path, 'r') as f:
                                f.read(1)
                            actions.append(f"{path_str} is readable")
                            
                            # Проверяем возможность записи
                            with open(path, 'a') as f:
                                pass
                            actions.append(f"{path_str} is writable")
                        
                        elif path.is_dir():
                            # Проверяем права на директорию
                            test_file = path / '.permission_test'
                            test_file.write_text('test')
                            test_file.unlink()
                            actions.append(f"{path_str} directory is writable")
                            
                    except PermissionError as e:
                        # Пытаемся исправить права (может не сработать в контейнере)
                        try:
                            if os.name == 'posix':
                                os.chmod(path, 0o666 if path.is_file() else 0o777)
                                actions.append(f"Fixed permissions for {path_str}")
                            else:
                                actions.append(f"Cannot fix permissions for {path_str} on this system")
                        except Exception:
                            success = False
                            actions.append(f"Failed to fix permissions for {path_str}: {e}")
                    
                    except Exception as e:
                        actions.append(f"Permission check failed for {path_str}: {e}")
            
        except Exception as e:
            success = False
            actions.append(f"Permission recovery failed: {e}")
        
        return {
            "success": success,
            "actions": actions
        }
    
    async def recover_token_issues(self, crash_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Восстановление проблем с токенами"""
        actions = []
        success = True
        
        try:
            # Проверяем наличие токенов
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
            admin_id = os.getenv('ADMIN_TELEGRAM_ID')
            
            if not telegram_token:
                success = False
                actions.append("TELEGRAM_BOT_TOKEN is missing")
            else:
                actions.append("TELEGRAM_BOT_TOKEN is present")
                
                # Проверяем валидность токена
                try:
                    bot = telegram.Bot(token=telegram_token)
                    me = await bot.get_me()
                    actions.append(f"Token is valid for bot: {me.username}")
                except Exception as e:
                    success = False
                    actions.append(f"Token validation failed: {e}")
            
            if not admin_id:
                actions.append("ADMIN_TELEGRAM_ID is missing (optional)")
            else:
                actions.append(f"ADMIN_TELEGRAM_ID is set: {admin_id}")
            
            # Проверяем другие токены
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                actions.append("GITHUB_TOKEN is present")
            else:
                actions.append("GITHUB_TOKEN is missing (optional)")
            
        except Exception as e:
            success = False
            actions.append(f"Token recovery failed: {e}")
        
        return {
            "success": success,
            "actions": actions
        }
    
    async def recover_general_restart(self, crash_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Общий перезапуск системы"""
        actions = []
        success = True
        
        try:
            # Очищаем временные файлы
            temp_patterns = [
                '*.tmp',
                '*.temp',
                '.DS_Store',
                'Thumbs.db'
            ]
            
            for pattern in temp_patterns:
                for temp_file in Path('.').rglob(pattern):
                    try:
                        temp_file.unlink()
                        actions.append(f"Removed temp file: {temp_file}")
                    except Exception:
                        pass
            
            # Сохраняем состояние
            state_file = Path('recovery_state.json')
            state = {
                "last_recovery": datetime.now().isoformat(),
                "crash_id": crash_analysis.get('crash_id'),
                "recovery_attempt": len(self.recovery_log) + 1
            }
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            actions.append("Recovery state saved")
            
            # В Railway контейнер перезапустится автоматически при завершении процесса
            # Оставляем специальный файл-флаг для следующего запуска
            restart_flag = Path('.recovery_restart_flag')
            restart_flag.write_text(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "reason": "auto_recovery",
                "crash_id": crash_analysis.get('crash_id')
            }))
            
            actions.append("Restart flag created")
            actions.append("System will restart automatically")
            
        except Exception as e:
            success = False
            actions.append(f"General restart preparation failed: {e}")
        
        return {
            "success": success,
            "actions": actions
        }
    
    async def _notify_recovery_start(self, crash_analysis: Dict[str, Any], strategy: List[str]):
        """Уведомление о начале восстановления"""
        if not self.telegram_token or not self.admin_chat_id:
            return
        
        try:
            bot = telegram.Bot(token=self.telegram_token)
            
            crash_id = crash_analysis.get('crash_id', 'unknown')
            strategy_text = '\n'.join([f"• {action}" for action in strategy])
            
            message = f"""🔧 **АВТОМАТИЧЕСКОЕ ВОССТАНОВЛЕНИЕ ЗАПУЩЕНО**

🆔 **Crash ID**: `{crash_id}`
⏰ **Время**: {datetime.now().strftime('%H:%M:%S')}

🎯 **Стратегия восстановления**:
{strategy_text}

⚙️ Выполняется автоматическое восстановление...
"""
            
            await bot.send_message(
                chat_id=self.admin_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            railway_logger.error(f"Failed to send recovery start notification: {e}", exc_info=True)
    
    async def _notify_recovery_complete(self, recovery_result: Dict[str, Any]):
        """Уведомление о завершении восстановления"""
        if not self.telegram_token or not self.admin_chat_id:
            return
        
        try:
            bot = telegram.Bot(token=self.telegram_token)
            
            crash_id = recovery_result.get('crash_id', 'unknown')
            success = recovery_result.get('success', False)
            actions = recovery_result.get('actions_taken', [])
            
            status_emoji = "✅" if success else "❌"
            status_text = "УСПЕШНО" if success else "НЕУСПЕШНО"
            
            actions_text = ""
            for action in actions:
                action_status = "✅" if action['result'].get('success', False) else "❌"
                actions_text += f"{action_status} {action['action']}\n"
            
            message = f"""{status_emoji} **АВТОМАТИЧЕСКОЕ ВОССТАНОВЛЕНИЕ {status_text}**

🆔 **Crash ID**: `{crash_id}`
⏰ **Завершено**: {datetime.now().strftime('%H:%M:%S')}

🛠 **Выполненные действия**:
{actions_text}

{'🎉 Система восстановлена!' if success else '⚠️ Требуется ручное вмешательство'}
"""
            
            await bot.send_message(
                chat_id=self.admin_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            railway_logger.error(f"Failed to send recovery complete notification: {e}", exc_info=True)
    
    async def _notify_recovery_error(self, recovery_result: Dict[str, Any], error: Exception):
        """Уведомление об ошибке восстановления"""
        if not self.telegram_token or not self.admin_chat_id:
            return
        
        try:
            bot = telegram.Bot(token=self.telegram_token)
            
            crash_id = recovery_result.get('crash_id', 'unknown')
            
            message = f"""💥 **ОШИБКА АВТОМАТИЧЕСКОГО ВОССТАНОВЛЕНИЯ**

🆔 **Crash ID**: `{crash_id}`
⏰ **Время**: {datetime.now().strftime('%H:%M:%S')}

❌ **Ошибка**: {str(error)[:200]}

🚨 Требуется немедленное ручное вмешательство!
"""
            
            await bot.send_message(
                chat_id=self.admin_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            railway_logger.error(f"Failed to send recovery error notification: {e}", exc_info=True)
    
    def _save_recovery_log(self):
        """Сохраняет лог восстановления"""
        try:
            log_file = Path('recovery_log.json')
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self.recovery_log, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            railway_logger.error(f"Failed to save recovery log: {e}", exc_info=True)
    
    def get_recovery_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Возвращает историю восстановлений за последние дни"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_recoveries = []
        for recovery in self.recovery_log:
            try:
                recovery_time = datetime.fromisoformat(recovery['timestamp'])
                if recovery_time > cutoff_date:
                    recent_recoveries.append(recovery)
            except (ValueError, TypeError):
                continue
        
        return recent_recoveries

# Глобальный экземпляр
auto_recovery = AutoRecoverySystem()

if __name__ == "__main__":
    # Тест системы автоматического восстановления
    print("Testing auto recovery system...")
    
    # Симулируем анализ краша
    mock_crash_analysis = {
        "crash_id": "test_crash_123",
        "primary_issue": {
            "exception_type": "requests.exceptions.ConnectionError",
            "category": "network"
        },
        "network_issues": {
            "connectivity_score": 30
        }
    }
    
    async def test_recovery():
        result = await auto_recovery.attempt_auto_recovery(mock_crash_analysis)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    asyncio.run(test_recovery())
