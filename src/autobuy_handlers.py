"""
Обработчики команд для автопокупки билетов.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

try:
    from .managers.account_manager import AccountManager
    from .utils.ticket_buyer import TicketBuyer, AuthenticationError, BookingError
except ImportError:
    from src.managers.account_manager import AccountManager
    from src.utils.ticket_buyer import TicketBuyer, AuthenticationError, BookingError

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    ACCOUNT_PHONE,
    ACCOUNT_PASSWORD,
    AUTOBUY_FROM,
    AUTOBUY_TO,
    AUTOBUY_DATE,
    AUTOBUY_TIME,
    AUTOBUY_CONFIRM
) = range(7)

# Инициализируем менеджер аккаунтов
account_manager = AccountManager()


async def account_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления аккаунтом"""
    user_id = update.effective_user.id
    has_account = account_manager.has_account(user_id)
    
    keyboard = []
    
    if has_account:
        keyboard.append([InlineKeyboardButton("🔄 Изменить аккаунт", callback_data="account_change")])
    else:
        keyboard.append([InlineKeyboardButton("➕ Добавить аккаунт", callback_data="account_add")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🔐 <b>Управление аккаунтом</b>\n\n"
        "Для автоматической покупки билетов необходимо "
        "привязать аккаунт с сайта маршруток.\n\n"
    )
    
    if has_account:
        text += "✅ Ваш аккаунт подключен и готов к использованию."
    else:
        text += "⚠️ Аккаунт не подключен. Добавьте учетные данные для автопокупки."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


async def account_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления аккаунта"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📱 <b>Добавление аккаунта</b>\n\n"
        "Введите номер телефона (без кода страны +375):\n"
        "Например: <code>299605390</code>\n\n"
        "Отправьте /cancel для отмены.",
        parse_mode='HTML'
    )
    return ACCOUNT_PHONE


async def account_phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получен номер телефона"""
    phone = update.message.text.strip()
    
    # Валидация номера телефона
    if not phone.isdigit() or len(phone) != 9:
        await update.message.reply_text(
            "❌ Неверный формат номера.\n"
            "Введите 9 цифр без пробелов и символов.\n"
            "Например: <code>299605390</code>",
            parse_mode='HTML'
        )
        return ACCOUNT_PHONE
    
    context.user_data['account_phone'] = phone
    
    await update.message.reply_text(
        "🔑 <b>Введите пароль</b>\n\n"
        "Пароль от вашего аккаунта на сайте маршруток.\n\n"
        "⚠️ <i>Пароль будет сохранен в зашифрованном виде.</i>",
        parse_mode='HTML'
    )
    return ACCOUNT_PASSWORD


async def account_password_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получен пароль"""
    password = update.message.text.strip()
    phone = context.user_data.get('account_phone')
    user_id = update.effective_user.id
    
    # Удаляем сообщение с паролем
    try:
        await update.message.delete()
    except:
        pass
    
    # Сохраняем аккаунт
    success = account_manager.add_account(user_id, phone, password)
    
    if success:
        await update.message.reply_text(
            "✅ <b>Аккаунт успешно добавлен!</b>\n\n"
            "Теперь вы можете использовать автопокупку билетов.\n"
            "Используйте команду /autobuy для начала.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при сохранении аккаунта.\n"
            "Попробуйте еще раз позже.",
            parse_mode='HTML'
        )
    
    # Очищаем данные
    context.user_data.clear()
    return ConversationHandler.END


async def account_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменение аккаунта - запускаем процесс добавления заново"""
    return await account_add_start(update, context)


async def autobuy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса автопокупки"""
    user_id = update.effective_user.id
    
    # Проверяем наличие аккаунта
    if not account_manager.has_account(user_id):
        keyboard = [[InlineKeyboardButton("➕ Добавить аккаунт", callback_data="account_add")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ <b>Аккаунт не подключен</b>\n\n"
            "Для автопокупки билетов необходимо добавить аккаунт.\n"
            "Нажмите кнопку ниже, чтобы начать.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🎫 <b>Автопокупка билета</b>\n\n"
        "Введите город отправления:\n"
        "Например: <code>Минск</code>\n\n"
        "Отправьте /cancel для отмены.",
        parse_mode='HTML'
    )
    return AUTOBUY_FROM


async def autobuy_from_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получен город отправления"""
    from_city = update.message.text.strip()
    context.user_data['autobuy_from'] = from_city
    
    await update.message.reply_text(
        "🎫 <b>Автопокупка билета</b>\n\n"
        f"Откуда: <b>{from_city}</b>\n\n"
        "Введите город назначения:\n"
        "Например: <code>Островец</code>",
        parse_mode='HTML'
    )
    return AUTOBUY_TO


async def autobuy_to_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получен город назначения"""
    to_city = update.message.text.strip()
    context.user_data['autobuy_to'] = to_city
    
    from_city = context.user_data.get('autobuy_from')
    
    await update.message.reply_text(
        "🎫 <b>Автопокупка билета</b>\n\n"
        f"Откуда: <b>{from_city}</b>\n"
        f"Куда: <b>{to_city}</b>\n\n"
        "Введите дату поездки:\n"
        "Формат: <code>ГГГГ-ММ-ДД</code>\n"
        "Например: <code>2025-11-09</code>",
        parse_mode='HTML'
    )
    return AUTOBUY_DATE


async def autobuy_date_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получена дата"""
    date = update.message.text.strip()
    
    # Валидация даты
    from datetime import datetime
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты.\n"
            "Используйте формат: <code>ГГГГ-ММ-ДД</code>\n"
            "Например: <code>2025-11-09</code>",
            parse_mode='HTML'
        )
        return AUTOBUY_DATE
    
    context.user_data['autobuy_date'] = date
    
    from_city = context.user_data.get('autobuy_from')
    to_city = context.user_data.get('autobuy_to')
    
    await update.message.reply_text(
        "🎫 <b>Автопокупка билета</b>\n\n"
        f"Откуда: <b>{from_city}</b>\n"
        f"Куда: <b>{to_city}</b>\n"
        f"Дата: <b>{date}</b>\n\n"
        "Введите предпочитаемое время отправления (необязательно):\n"
        "Формат: <code>ЧЧ:ММ</code>\n"
        "Например: <code>07:00</code>\n\n"
        "Или отправьте <code>-</code> для пропуска.",
        parse_mode='HTML'
    )
    return AUTOBUY_TIME


async def autobuy_time_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получено время"""
    time_text = update.message.text.strip()
    
    preferred_time = None
    if time_text != '-':
        preferred_time = time_text
    
    context.user_data['autobuy_time'] = preferred_time
    
    from_city = context.user_data.get('autobuy_from')
    to_city = context.user_data.get('autobuy_to')
    date = context.user_data.get('autobuy_date')
    
    text = (
        "🎫 <b>Подтверждение автопокупки</b>\n\n"
        f"Откуда: <b>{from_city}</b>\n"
        f"Куда: <b>{to_city}</b>\n"
        f"Дата: <b>{date}</b>\n"
    )
    
    if preferred_time:
        text += f"Время: <b>{preferred_time}</b>\n"
    
    text += "\nБот автоматически найдет и купит билет.\n\n⚠️ Подтвердите покупку:"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Купить", callback_data="autobuy_confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data="autobuy_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return AUTOBUY_CONFIRM


async def autobuy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и выполнение автопокупки"""
    await update.callback_query.answer()
    user_id = update.effective_user.id
    
    # Получаем данные
    from_city = context.user_data.get('autobuy_from')
    to_city = context.user_data.get('autobuy_to')
    date = context.user_data.get('autobuy_date')
    preferred_time = context.user_data.get('autobuy_time')
    
    # Получаем учетные данные
    account = account_manager.get_account(user_id)
    if not account:
        await update.callback_query.edit_message_text(
            "❌ Ошибка: аккаунт не найден.\n"
            "Пожалуйста, добавьте аккаунт заново."
        )
        return ConversationHandler.END
    
    # Показываем сообщение о начале процесса
    await update.callback_query.edit_message_text(
        "⏳ <b>Идет поиск и покупка билета...</b>\n\n"
        "Это может занять некоторое время.\n"
        "Пожалуйста, подождите.",
        parse_mode='HTML'
    )
    
    try:
        # Создаем покупателя билетов
        async with TicketBuyer(
            phone=account['phone'],
            password=account['password'],
            headless=True
        ) as buyer:
            # Выполняем автопокупку
            result = await buyer.auto_buy_ticket(
                from_city=from_city,
                to_city=to_city,
                date=date,
                preferred_time=preferred_time,
                min_seats=1
            )
            
            # Формируем сообщение о результате
            if result.get('success'):
                text = (
                    "✅ <b>Билет успешно куплен!</b>\n\n"
                    f"Маршрут: <b>{result.get('Маршрут:', 'N/A')}</b>\n"
                    f"Отправление: <b>{result.get('Отправление:', 'N/A')}</b>\n"
                    f"Прибытие: <b>{result.get('Прибытие:', 'N/A')}</b>\n"
                    f"Место №: <b>{result.get('seat_number', 'N/A')}</b>\n"
                    f"Цена: <b>{result.get('price', 'N/A')} BYN</b>\n\n"
                    "Проверьте раздел 'Мои билеты' на сайте."
                )
            else:
                text = (
                    "⚠️ <b>Билет забронирован (требуется проверка)</b>\n\n"
                    f"Маршрут: <b>{result.get('Маршрут:', 'N/A')}</b>\n"
                    f"Отправление: <b>{result.get('Отправление:', 'N/A')}</b>\n\n"
                    "Пожалуйста, проверьте статус на сайте."
                )
            
            await update.callback_query.edit_message_text(
                text=text,
                parse_mode='HTML'
            )
            
    except AuthenticationError as e:
        # Экранируем HTML-теги в сообщении об ошибке
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await update.callback_query.edit_message_text(
            f"❌ <b>Ошибка авторизации</b>\n\n"
            f"Не удалось войти в аккаунт.\n"
            f"Проверьте правильность учетных данных.\n\n"
            f"Ошибка: <code>{error_msg}</code>",
            parse_mode='HTML'
        )
    except BookingError as e:
        # Экранируем HTML-теги в сообщении об ошибке
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await update.callback_query.edit_message_text(
            f"❌ <b>Ошибка бронирования</b>\n\n"
            f"{error_msg}",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка при автопокупке: {e}", exc_info=True)
        await update.callback_query.edit_message_text(
            f"❌ <b>Произошла ошибка</b>\n\n"
            f"Не удалось выполнить автопокупку.\n"
            f"Попробуйте еще раз позже.\n\n"
            f"Ошибка: <code>{str(e)}</code>",
            parse_mode='HTML'
        )
    
    # Очищаем данные
    context.user_data.clear()
    return ConversationHandler.END


async def autobuy_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена автопокупки"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "❌ Автопокупка отменена."
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущей операции"""
    await update.message.reply_text(
        "❌ Операция отменена."
    )
    context.user_data.clear()
    return ConversationHandler.END


def get_account_handlers():
    """Получить обработчики для управления аккаунтом"""
    account_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(account_add_start, pattern="^account_add$")],
        states={
            ACCOUNT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_phone_received)],
            ACCOUNT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_password_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="account_conversation",
        persistent=False
    )
    
    return [
        CommandHandler("account", account_menu),
        CallbackQueryHandler(account_menu, pattern="^account_menu$"),
        CallbackQueryHandler(account_change, pattern="^account_change$"),
        account_conv_handler
    ]


def get_autobuy_handlers():
    """Получить обработчики для автопокупки"""
    autobuy_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("autobuy", autobuy_start)],
        states={
            AUTOBUY_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, autobuy_from_received)],
            AUTOBUY_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, autobuy_to_received)],
            AUTOBUY_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, autobuy_date_received)],
            AUTOBUY_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, autobuy_time_received)],
            AUTOBUY_CONFIRM: [
                CallbackQueryHandler(autobuy_confirm, pattern="^autobuy_confirm$"),
                CallbackQueryHandler(autobuy_cancel, pattern="^autobuy_cancel$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="autobuy_conversation",
        persistent=False
    )
    
    return [autobuy_conv_handler]
