import os
import logging
from logging.handlers import RotatingFileHandler
import telegram
import asyncio
from datetime import datetime
import traceback

try:
    from .railway_logger_enhanced import RailwayLoggerEnhanced as RailwayLogger
except ImportError:
    # Заглушка если модуль недоступен
    class RailwayLogger:
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(__name__)

class TelegramLogHandler(logging.Handler):
    def __init__(self, bot_token, chat_id):
        super().__init__()
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = telegram.Bot(token=bot_token)
        self.buffer = []
        self.buffer_size = 10
        self.last_send_time = datetime.now()
        self.send_interval = 60  # секунд

    def emit(self, record):
        log_entry = self.format(record)
        
        # Добавляем запись в буфер
        if record.levelno >= logging.ERROR:
            # Для ошибок и критических сообщений добавляем трейсбек
            if record.exc_info:
                log_entry += f"\n\n```\n{traceback.format_exception(*record.exc_info)[-1]}```"
            
            self.buffer.append(f"🔴 ОШИБКА: {log_entry}")
            # Ошибки отправляем сразу
            asyncio.create_task(self.flush_buffer(force=True))
        elif record.levelno >= logging.WARNING:
            self.buffer.append(f"🟠 ПРЕДУПРЕЖДЕНИЕ: {log_entry}")
        else:
            # Информационные сообщения добавляем только если они важные
            if "запуск" in log_entry.lower() or "старт" in log_entry.lower() or "стоп" in log_entry.lower():
                self.buffer.append(f"🟢 ИНФО: {log_entry}")
        
        # Проверяем необходимость отправки буфера
        now = datetime.now()
        time_diff = (now - self.last_send_time).total_seconds()
        
        if len(self.buffer) >= self.buffer_size or time_diff >= self.send_interval:
            asyncio.create_task(self.flush_buffer())

    async def flush_buffer(self, force=False):
        if not self.buffer:
            return
        
        if not force and len(self.buffer) < self.buffer_size:
            now = datetime.now()
            if (now - self.last_send_time).total_seconds() < self.send_interval:
                return
        
        try:
            message = f"📋 Логи от {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}:\n\n"
            message += "\n\n".join(self.buffer[-10:])  # Отправляем последние 10 сообщений
            
            if len(message) > 4000:
                message = message[:3997] + "..."
                
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            self.last_send_time = datetime.now()
            self.buffer = []
        except Exception as e:
            print(f"Ошибка при отправке логов в Telegram: {e}")

def setup_logging(log_level=logging.INFO):
    """Настройка логирования с отправкой в Telegram и Railway-оптимизацией"""
    
    # Определяем, работаем ли мы в Railway
    in_railway = os.getenv('RAILWAY_SERVICE_NAME') is not None
    
    if in_railway:
        # Используем Railway logger для продакшена
        logger = RailwayLogger("MarhrutochkaTG")
        logger.info("🚂 Система логирования настроена для Railway", 
                   extra={"component": "log_manager", "environment": "railway"})
        return logger
    
    # Локальная разработка - стандартное логирование
    # Создаем папку для логов, если её нет
    os.makedirs('logs', exist_ok=True)
    
    # Основной логгер
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Форматирование
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Хендлер для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Хендлер для записи в файл
    file_handler = RotatingFileHandler(
        'data/logs/bot.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Хендлер для отправки в Telegram, если заданы переменные окружения
    log_bot_token = os.getenv('LOG_BOT_TOKEN')
    log_chat_id = os.getenv('LOG_CHAT_ID')
    
    if log_bot_token and log_chat_id:
        telegram_handler = TelegramLogHandler(log_bot_token, log_chat_id)
        telegram_handler.setFormatter(formatter)
        telegram_handler.setLevel(logging.WARNING)  # Отправляем только warnings и ошибки
        logger.addHandler(telegram_handler)
    
    return logger

# Пример использования
if __name__ == "__main__":
    logger = setup_logging()
    
    # Проверяем тип логгера
    if isinstance(logger, RailwayLogger):
        logger.bot_action("Тест Railway логирования", {"status": "test"})
        logger.warning("Тест Railway предупреждения")
        try:
            1/0
        except Exception as e:
            logger.error(f"Тест Railway ошибки: {e}", exc_info=True)
    else:
        logger.info("Тест локального логирования: INFO")
        logger.warning("Тест локального логирования: WARNING")
        try:
            1/0
        except Exception as e:
            logger.error(f"Тест локального логирования: ERROR - {e}", exc_info=True)
