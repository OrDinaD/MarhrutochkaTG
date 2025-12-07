#!/usr/bin/env python3
"""
Система автоматического сбора крашей и диагностики
Собирает информацию об ошибках и отправляет детальные отчеты для удаленной диагностики
"""

import os
import sys
import json
import time
import traceback
import platform
import subprocess
import psutil
import aiohttp
import requests  # Keep requests for sync crash handling if needed, but prefer aiohttp for async
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio
import telegram
from .railway_logger_enhanced import railway_logger

class CrashHandler:
    """Обработчик крашей с автоматической диагностикой"""
    
    def __init__(self):
        self.crash_id = None
        self.crash_data = {}
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_chat_id = os.getenv('ADMIN_TELEGRAM_ID')
        self.github_token = os.getenv('GITHUB_TOKEN')  # Для создания Gists
        self.crash_logs_dir = Path('crash_logs')
        self.crash_logs_dir.mkdir(exist_ok=True)
        
    def collect_system_info(self) -> Dict[str, Any]:
        """Собирает информацию о системе"""
        try:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "python_version": platform.python_version(),
                    "python_implementation": platform.python_implementation()
                },
                "environment": {
                    "railway_service": os.getenv('RAILWAY_SERVICE_NAME'),
                    "railway_replica": os.getenv('RAILWAY_REPLICA_ID'),
                    "railway_region": os.getenv('RAILWAY_REPLICA_REGION'),
                    "log_level": os.getenv('LOG_LEVEL'),
                    "working_directory": os.getcwd(),
                    "python_path": sys.executable,
                    "process_id": os.getpid()
                },
                "resources": {
                    "cpu_count": psutil.cpu_count(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory": {
                        "total": psutil.virtual_memory().total,
                        "available": psutil.virtual_memory().available,
                        "percent": psutil.virtual_memory().percent,
                        "used": psutil.virtual_memory().used
                    },
                    "disk": {
                        "total": psutil.disk_usage('/').total,
                        "used": psutil.disk_usage('/').used,
                        "free": psutil.disk_usage('/').free,
                        "percent": psutil.disk_usage('/').percent
                    }
                }
            }
        except Exception as e:
            return {"error": f"Failed to collect system info: {e}"}
    
    def collect_dependencies_info(self) -> Dict[str, Any]:
        """Собирает информацию о зависимостях"""
        try:
            # Получаем список установленных пакетов
            result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                packages = json.loads(result.stdout)
                return {
                    "installed_packages": packages,
                    "requirements_file": self._read_requirements()
                }
            else:
                return {"error": f"Failed to get pip list: {result.stderr}"}
        except Exception as e:
            return {"error": f"Failed to collect dependencies: {e}"}
    
    def _read_requirements(self) -> Optional[str]:
        """Читает файл requirements.txt"""
        try:
            req_file = Path('requirements.txt')
            if req_file.exists():
                return req_file.read_text()
            return None
        except Exception:
            return None
    
    def collect_application_state(self) -> Dict[str, Any]:
        """Собирает состояние приложения"""
        try:
            app_state = {
                "config_files": {},
                "log_files": {},
                "data_files": {},
                "process_info": {}
            }
            
            # Проверяем конфигурационные файлы
            config_files = ['main.py', 'Procfile', '.env.example']
            for file_name in config_files:
                file_path = Path(file_name)
                if file_path.exists():
                    try:
                        app_state["config_files"][file_name] = {
                            "exists": True,
                            "size": file_path.stat().st_size,
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        }
                        # Для некритичных файлов читаем содержимое
                        if file_name == 'Procfile':
                            app_state["config_files"][file_name]["content"] = file_path.read_text()
                    except Exception as e:
                        app_state["config_files"][file_name] = {"error": str(e)}
            
            # Проверяем файлы логов
            log_files = ['data/logs/bot.log', 'data/crash_logs/']
            for log_path in log_files:
                path = Path(log_path)
                if path.exists():
                    if path.is_file():
                        app_state["log_files"][log_path] = {
                            "size": path.stat().st_size,
                            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                            "last_lines": self._get_file_tail(path)
                        }
                    elif path.is_dir():
                        app_state["log_files"][log_path] = {
                            "type": "directory",
                            "files": [f.name for f in path.iterdir()]
                        }
            
            # Проверяем файлы данных
            data_files = ['data/monitors.json']  # user_sessions.json удален
            for data_file in data_files:
                file_path = Path(data_file)
                if file_path.exists():
                    try:
                        app_state["data_files"][data_file] = {
                            "size": file_path.stat().st_size,
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        }
                        # Пытаемся прочитать как JSON для проверки валидности
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            app_state["data_files"][data_file]["valid_json"] = True
                            app_state["data_files"][data_file]["keys_count"] = len(data) if isinstance(data, dict) else "not_dict"
                    except json.JSONDecodeError:
                        app_state["data_files"][data_file]["valid_json"] = False
                    except Exception as e:
                        app_state["data_files"][data_file]["error"] = str(e)
            
            return app_state
            
        except Exception as e:
            return {"error": f"Failed to collect application state: {e}"}
    
    def _get_file_tail(self, file_path: Path, lines: int = 50) -> List[str]:
        """Получает последние строки файла"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.readlines()[-lines:]
        except Exception:
            return []
    
    def collect_network_info(self) -> Dict[str, Any]:
        """Собирает информацию о сети"""
        try:
            network_info = {
                "connections": [],
                "interfaces": {},
                "external_connectivity": {}
            }
            
            # Проверяем сетевые соединения
            connections = psutil.net_connections(kind='inet')
            for conn in connections[:10]:  # Ограничиваем количество
                network_info["connections"].append({
                    "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid
                })
            
            # Проверяем сетевые интерфейсы
            interfaces = psutil.net_if_addrs()
            for interface, addrs in interfaces.items():
                network_info["interfaces"][interface] = []
                for addr in addrs:
                    network_info["interfaces"][interface].append({
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    })
            
            # Проверяем внешнюю связность
            test_urls = [
                "https://api.telegram.org",
                "https://httpbin.org/ip",
                "https://api.github.com"
            ]
            
            for url in test_urls:
                try:
                    response = requests.get(url, timeout=5)
                    network_info["external_connectivity"][url] = {
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds(),
                        "accessible": True
                    }
                except Exception as e:
                    network_info["external_connectivity"][url] = {
                        "accessible": False,
                        "error": str(e)
                    }
            
            return network_info
            
        except Exception as e:
            return {"error": f"Failed to collect network info: {e}"}
    
    def generate_crash_report(self, exception: Exception, tb_str: str) -> Dict[str, Any]:
        """Генерирует полный отчет о краше"""
        self.crash_id = f"crash_{int(time.time())}_{os.getpid()}"
        
        crash_report = {
            "crash_id": self.crash_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exception": {
                "type": type(exception).__name__,
                "message": str(exception),
                "module": getattr(exception, '__module__', 'unknown'),
                "traceback": tb_str,
                "traceback_lines": tb_str.split('\n')
            },
            "system_info": self.collect_system_info(),
            "dependencies": self.collect_dependencies_info(),
            "application_state": self.collect_application_state(),
            "network_info": self.collect_network_info()
        }
        
        return crash_report
    
    def save_crash_report(self, crash_report: Dict[str, Any]) -> Path:
        """Сохраняет отчет о краше локально"""
        crash_file = self.crash_logs_dir / f"{self.crash_id}.json"
        
        try:
            with open(crash_file, 'w', encoding='utf-8') as f:
                json.dump(crash_report, f, indent=2, ensure_ascii=False, default=str)
            
            return crash_file
        except Exception as e:
            # Fallback - сохраняем в текущую директорию
            fallback_file = Path(f"{self.crash_id}_fallback.json")
            try:
                with open(fallback_file, 'w', encoding='utf-8') as f:
                    json.dump(crash_report, f, indent=2, ensure_ascii=False, default=str)
                return fallback_file
            except Exception:
                return None
    
    async def send_crash_notification(self, crash_report: Dict[str, Any], crash_file: Optional[Path] = None):
        """Отправляет уведомление о краше администратору"""
        if not self.telegram_token or not self.admin_chat_id:
            return
        
        try:
            bot = telegram.Bot(token=self.telegram_token)
            
            # Создаем краткое сообщение
            exception_info = crash_report.get('exception', {})
            system_info = crash_report.get('system_info', {})
            
            message = f"""🔥 **КРИТИЧЕСКИЙ КРАШ ПРИЛОЖЕНИЯ**
            
🆔 **Crash ID**: `{crash_report['crash_id']}`
📅 **Время**: {crash_report['timestamp']}

❌ **Ошибка**: {exception_info.get('type', 'Unknown')}
💬 **Сообщение**: {exception_info.get('message', 'No message')[:200]}

🖥 **Система**: {system_info.get('platform', {}).get('system', 'Unknown')}
🐍 **Python**: {system_info.get('platform', {}).get('python_version', 'Unknown')}
🚂 **Railway**: {system_info.get('environment', {}).get('railway_service', 'Unknown')}

📊 **CPU**: {system_info.get('resources', {}).get('cpu_percent', 'Unknown')}%
💾 **RAM**: {system_info.get('resources', {}).get('memory', {}).get('percent', 'Unknown')}%

🔍 **Для диагностики используйте**: `/diagnose {crash_report['crash_id']}`
"""
            
            await bot.send_message(
                chat_id=self.admin_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            # Отправляем файл отчета, если он создался
            if crash_file and crash_file.exists():
                await bot.send_document(
                    chat_id=self.admin_chat_id,
                    document=crash_file,
                    caption=f"Полный отчет о краше {crash_report['crash_id']}"
                )
            
        except Exception as e:
            railway_logger.error(f"Failed to send crash notification: {e}", exc_info=True)
    
    async def upload_to_github_gist(self, crash_report: Dict[str, Any]) -> Optional[str]:
        """Загружает отчет в GitHub Gist для удаленного доступа"""
        if not self.github_token:
            return None
        
        try:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            gist_data = {
                "description": f"Crash Report {crash_report['crash_id']} - {crash_report['timestamp']}",
                "public": False,
                "files": {
                    f"{crash_report['crash_id']}.json": {
                        "content": json.dumps(crash_report, indent=2, ensure_ascii=False, default=str)
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.github.com/gists',
                    headers=headers,
                    json=gist_data,
                    timeout=10
                ) as response:
                    if response.status == 201:
                        data = await response.json()
                        gist_url = data.get('html_url')
                        return gist_url
            
        except Exception as e:
            railway_logger.error(f"Failed to upload to GitHub Gist: {e}", exc_info=True)
        
        return None
    
    def _generate_crash_id(self) -> str:
        """Генерирует уникальный ID краша"""
        import uuid
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"crash_{timestamp}_{unique_id}"
    
    def handle_crash(self, exception: Exception, tb_str=None):
        """Синхронный обработчик крашей"""
        try:
            crash_id = self._generate_crash_id()
            railway_logger.crash_event(f"CRASH DETECTED: {type(exception).__name__}: {exception}", crash_id, data={"exception": str(exception)})
            
            # Если tb_str не передан или это dict, получаем traceback
            if tb_str is None or isinstance(tb_str, dict):
                tb_str = traceback.format_exc()
            
            # Генерируем отчет о краше
            crash_report = self.generate_crash_report(exception, tb_str)
            crash_report['crash_id'] = crash_id
            
            # Сохраняем локально
            crash_file = self.save_crash_report(crash_report)
            railway_logger.info(f"💾 Crash report saved: {crash_file}", extra={"filepath": str(crash_file)})
            
            # Отправляем уведомление асинхронно
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._async_crash_handling(crash_report, crash_file))
                loop.close()
            except Exception as e:
                railway_logger.error(f"⚠️ Failed to send crash notification: {e}", exc_info=True)
            
        except Exception as e:
            railway_logger.error(f"❌ Error in crash handler: {e}", exc_info=True)
            traceback.print_exc()
    
    def setup_crash_handling(self):
        """Настраивает обработку крашей"""
        def custom_excepthook(exc_type, exc_value, exc_traceback):
            """Кастомный обработчик исключений"""
            if issubclass(exc_type, KeyboardInterrupt):
                # Игнорируем KeyboardInterrupt (Ctrl+C)
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # Формируем строку traceback
            tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            
            # Обрабатываем краш
            try:
                self.handle_crash(exc_value, tb_str)
            except Exception as e:
                # Если наш обработчик упал, используем стандартный
                print(f"Crash handler failed: {e}")
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
        
        # Устанавливаем кастомный обработчик
        sys.excepthook = custom_excepthook
        
        # Логируем активацию
        railway_logger.system_action("🛡️ Crash handler activated")
    
def setup_crash_handler():
    """Настраивает глобальный crash handler"""
    crash_handler.setup_crash_handling()

# Создаем глобальный экземпляр
crash_handler = CrashHandler()

if __name__ == "__main__":
    # Тестируем crash handler
    setup_crash_handler()
    
    # Симулируем краш
    try:
        raise Exception("Test crash for demonstration")
    except Exception as e:
        print("Exception handled by crash handler")
    
    async def _async_crash_handling(self, crash_report: Dict[str, Any], crash_file: Optional[Path]):
        """Асинхронная обработка краша"""
        # Отправляем уведомление
        await self.send_crash_notification(crash_report, crash_file)
        
        # Загружаем в GitHub Gist
        gist_url = await self.upload_to_github_gist(crash_report)
        if gist_url:
            railway_logger.info(f"🔗 Gist URL: {gist_url}", extra={"url": gist_url})

# Глобальный экземпляр
crash_handler = CrashHandler()

def setup_crash_handler():
    """Настраивает глобальный обработчик крашей"""
    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Обычное завершение программы
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Обрабатываем краш
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        crash_handler.handle_crash(exc_value, tb_str)
        
        # Вызываем стандартный обработчик
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_handler

if __name__ == "__main__":
    # Тест системы краш-обработки
    setup_crash_handler()
    
    # Симулируем краш
    print("Testing crash handler...")
    raise ValueError("Test crash for demonstration")
