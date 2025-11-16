#!/usr/bin/env python3
"""
Утилиты для безопасной работы с Telegram API
Объединяет повторяющиеся функции safe_*
"""
import asyncio
import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest


logger = logging.getLogger(__name__)


class TelegramSafeAPI:
    """Класс для безопасной работы с Telegram API"""
    
    @staticmethod
    async def safe_edit_message(
        query_or_update, 
        text: str, 
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: Optional[str] = None, 
        timeout: int = 10
    ):
        """Безопасное редактирование сообщения с обработкой ошибок и таймаутом"""
        try:
            async def _edit_message():
                if hasattr(query_or_update, 'edit_message_text'):
                    # Это CallbackQuery
                    await query_or_update.edit_message_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                elif hasattr(query_or_update, 'effective_message'):
                    # Это Update
                    await query_or_update.effective_message.edit_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
            
            # Выполняем с таймаутом
            await asyncio.wait_for(_edit_message(), timeout=timeout)
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Таймаут при редактировании сообщения ({timeout}s)")
            # Пытаемся отправить простое сообщение вместо редактирования
            try:
                if hasattr(query_or_update, 'message'):
                    await query_or_update.message.reply_text(text, reply_markup=reply_markup)
            except Exception:
                logger.error("Не удалось отправить сообщение после таймаута")
                
        except BadRequest as e:
            if "Message is not modified" in str(e):
                logger.debug("Сообщение не изменено")
            elif "Message to edit not found" in str(e):
                logger.warning("Сообщение для редактирования не найдено")
            else:
                logger.error(f"BadRequest при редактировании: {e}")
                
        except Exception as e:
            logger.error(f"Неожиданная ошибка при редактировании сообщения: {e}")

    @staticmethod
    async def safe_answer_callback(query, text: str = "", timeout: int = 5):
        """Безопасный ответ на callback query с таймаутом"""
        try:
            await asyncio.wait_for(query.answer(text), timeout=timeout)
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Таймаут при ответе на callback ({timeout}s)")
        except Exception as e:
            # Игнорируем ошибки о том, что callback уже был отвечен
            error_msg = str(e).lower()
            if any(msg in error_msg for msg in ["query is too old", "invalid query id", "already answered"]):
                logger.debug(f"Callback query устарел или уже отвечен: {e}")
            else:
                logger.error(f"Ошибка при ответе на callback: {e}")

    @staticmethod
    async def safe_send_message(
        update_or_context, 
        text: str, 
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: Optional[str] = None, 
        timeout: int = 10
    ):
        """Безопасная отправка сообщения с таймаутом"""
        try:
            async def _send_message():
                # Пытаемся отправить через сообщение апдейта
                message = getattr(update_or_context, 'message', None)
                if message:
                    await message.reply_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                    return

                effective_message = getattr(update_or_context, 'effective_message', None)
                if effective_message:
                    await effective_message.reply_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                    return

                # CallbackContext или подобные объекты
                if hasattr(update_or_context, 'bot'):
                    bot = update_or_context.bot
                    chat_id = getattr(update_or_context, 'chat_id', None)
                    if chat_id:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode
                        )
                        return

                # Словари/кастомные структуры (обратная совместимость)
                if isinstance(update_or_context, dict):
                    bot = update_or_context.get('bot')
                    chat_id = update_or_context.get('chat_id')
                    if bot and chat_id:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode
                        )
                        return

                logger.error("Не удалось определить получателя для safe_send_message")
                        
            await asyncio.wait_for(_send_message(), timeout=timeout)
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Таймаут при отправке сообщения ({timeout}s)")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")

    @staticmethod
    def callback_handler_protection(timeout: int = 30):
        """Улучшенный декоратор для защиты callback handlers от зависания"""
        def decorator(func):
            async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
                user_id = None
                try:
                    if update.effective_user:
                        user_id = update.effective_user.id
                    
                    # Выполняем функцию с таймаутом
                    return await asyncio.wait_for(
                        func(update, context, *args, **kwargs), 
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"⏰ [{user_id}] Таймаут callback handler {func.__name__} ({timeout}s)")
                    # Экстренный сброс состояния если нужно
                    if user_id and hasattr(context, 'user_data'):
                        context.user_data.clear()
                except Exception as e:
                    logger.error(f"❌ [{user_id}] Ошибка в callback handler {func.__name__}: {e}")
                
            return wrapper
        return decorator


# Создаем глобальные псевдонимы для обратной совместимости
safe_edit_message = TelegramSafeAPI.safe_edit_message
safe_answer_callback = TelegramSafeAPI.safe_answer_callback
safe_send_message = TelegramSafeAPI.safe_send_message
callback_handler_protection = TelegramSafeAPI.callback_handler_protection
