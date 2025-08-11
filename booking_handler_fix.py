# Код для добавления в bot.py

# Добавить новые состояния (в начало файла):
# BOOK_ROUTE_FROM, BOOK_ROUTE_TO, BOOK_ROUTE_DATE, BOOK_ROUTE_CONFIRM = range(18, 22)

async def handle_book_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс бронирования рейса"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем авторизацию
    if not bot_auth_manager.is_authenticated(user_id) and user_id not in user_sessions:
        await query.edit_message_text(
            "🔒 Необходимо войти в аккаунт для бронирования",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔒 Войти", callback_data="login_requests"),
                InlineKeyboardButton("🔙 Назад", callback_data="auto_booking")
            ]])
        )
        return
    
    await query.edit_message_text(
        "🛣️ **БРОНИРОВАНИЕ РЕЙСА**\n\n"
        "Шаг 1: Откуда отправляемся?\n\n"
        "💡 Введите город отправления:",
        parse_mode='Markdown'
    )
    
    return BOOK_ROUTE_FROM

async def book_route_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить город отправления"""
    from_city = update.message.text.strip()
    context.user_data['book_from'] = from_city
    
    await update.message.reply_text(
        f"✅ Отправление: **{from_city}**\n\n"
        f"🛣️ Шаг 2: Куда едем?\n\n"
        f"💡 Введите город назначения:",
        parse_mode='Markdown'
    )
    
    return BOOK_ROUTE_TO

async def book_route_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить город назначения"""
    to_city = update.message.text.strip()
    context.user_data['book_to'] = to_city
    
    await update.message.reply_text(
        f"✅ Маршрут: **{context.user_data['book_from']} → {to_city}**\n\n"
        f"📅 Шаг 3: Дата поездки\n\n"
        f"💡 Введите дату в формате ДД.ММ.ГГГГ\n"
        f"(например: 12.08.2025):",
        parse_mode='Markdown'
    )
    
    return BOOK_ROUTE_DATE

async def book_route_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить дату и показать доступные рейсы"""
    date_str = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Валидация даты
    try:
        from datetime import datetime
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        context.user_data['book_date'] = date_str
    except ValueError:
        await update.message.reply_text(
            "❌ Некорректная дата. Используйте формат ДД.ММ.ГГГГ\n"
            "Попробуйте снова:"
        )
        return BOOK_ROUTE_DATE
    
    # Получаем менеджер авторизации
    if bot_auth_manager.is_authenticated(user_id):
        auth_manager = bot_auth_manager.get_auth_manager(user_id)
    else:
        auth_manager = user_sessions.get(user_id)
    
    if not auth_manager:
        await update.message.reply_text("❌ Ошибка авторизации")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔍 Ищу доступные рейсы...\n"
        "⏳ Это может занять несколько секунд"
    )
    
    try:
        # Создаем менеджер бронирования
        booking_manager = AutoBookingManager(auth_manager)
        
        # Получаем доступные рейсы
        loop = asyncio.get_event_loop()
        routes = await loop.run_in_executor(
            None, 
            booking_manager.get_available_routes,
            context.user_data['book_from'],
            context.user_data['book_to'],
            context.user_data['book_date'],
            1
        )
        
        if not routes:
            await update.message.reply_text(
                f"😔 Рейсы не найдены\n\n"
                f"**Маршрут:** {context.user_data['book_from']} → {context.user_data['book_to']}\n"
                f"**Дата:** {date_str}\n\n"
                f"💡 Попробуйте:\n"
                f"• Проверить правильность названий городов\n"
                f"• Выбрать другую дату\n"
                f"• Поменять местами города",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Новый поиск", callback_data="book_route"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                ]])
            )
            return ConversationHandler.END
        
        # Сохраняем найденные рейсы
        context.user_data['available_routes'] = routes
        
        # Формируем сообщение с рейсами
        message_parts = [
            f"🎯 **НАЙДЕННЫЕ РЕЙСЫ**",
            f"",
            f"**Маршрут:** {context.user_data['book_from']} → {context.user_data['book_to']}",
            f"**Дата:** {date_str}",
            f"**Найдено:** {len(routes)} рейс(ов)",
            f"",
        ]
        
        # Показываем первые 5 рейсов
        buttons = []
        for i, route in enumerate(routes[:5]):
            route_info = (
                f"**{i+1}. {route.get('departure_time', 'н/д')} → {route.get('arrival_time', 'н/д')}**\n"
                f"   💰 {route.get('price', 'н/д')} BYN\n"
                f"   🪑 {route.get('available_seats', 0)} мест\n"
                f"   🚌 {route.get('carrier', 'н/д')}\n"
            )
            message_parts.append(route_info)
            
            # Кнопка для бронирования этого рейса
            buttons.append([InlineKeyboardButton(
                f"🎫 Забронировать рейс {i+1}",
                callback_data=f"confirm_booking_{i}"
            )])
        
        if len(routes) > 5:
            message_parts.append(f"... и еще {len(routes)-5} рейс(ов)")
        
        buttons.append([
            InlineKeyboardButton("🔄 Новый поиск", callback_data="book_route"),
            InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
        ])
        
        await update.message.reply_text(
            "\n".join(message_parts),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        return BOOK_ROUTE_CONFIRM
        
    except Exception as e:
        logger.error(f"Ошибка поиска рейсов: {e}")
        await update.message.reply_text(
            f"❌ Ошибка поиска рейсов: {str(e)}\n\n"
            f"💡 Попробуйте позже или обратитесь к администратору",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
            ]])
        )
        return ConversationHandler.END

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и выполнение бронирования"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Извлекаем индекс рейса из callback_data
    callback_data = query.data
    if not callback_data.startswith("confirm_booking_"):
        await query.answer("❌ Ошибка данных")
        return ConversationHandler.END
    
    try:
        route_index = int(callback_data.split("_")[-1])
        routes = context.user_data.get('available_routes', [])
        
        if route_index >= len(routes):
            await query.answer("❌ Рейс не найден")
            return ConversationHandler.END
        
        selected_route = routes[route_index]
        
        await query.edit_message_text(
            f"🎫 **ПОДТВЕРЖДЕНИЕ БРОНИРОВАНИЯ**\n\n"
            f"**Рейс:** {selected_route.get('departure_time')} → {selected_route.get('arrival_time')}\n"
            f"**Маршрут:** {context.user_data['book_from']} → {context.user_data['book_to']}\n"
            f"**Дата:** {context.user_data['book_date']}\n"
            f"**Стоимость:** {selected_route.get('price')} BYN\n"
            f"**Перевозчик:** {selected_route.get('carrier')}\n\n"
            f"🤖 Выполняю бронирование...",
            parse_mode='Markdown'
        )
        
        # Получаем менеджер авторизации
        if bot_auth_manager.is_authenticated(user_id):
            auth_manager = bot_auth_manager.get_auth_manager(user_id)
        else:
            auth_manager = user_sessions.get(user_id)
        
        # Выполняем бронирование
        booking_manager = AutoBookingManager(auth_manager)
        loop = asyncio.get_event_loop()
        
        booking_result = await loop.run_in_executor(
            None,
            booking_manager.auto_book_route,
            selected_route,
            1,  # 1 пассажир
            None  # Данные пассажира будут использованы из профиля
        )
        
        if booking_result.get('success'):
            booking_id = booking_result.get('booking_id', 'н/д')
            await query.edit_message_text(
                f"✅ **БРОНИРОВАНИЕ УСПЕШНО!**\n\n"
                f"🎫 **Номер бронирования:** {booking_id}\n"
                f"**Рейс:** {selected_route.get('departure_time')} → {selected_route.get('arrival_time')}\n"
                f"**Маршрут:** {context.user_data['book_from']} → {context.user_data['book_to']}\n"
                f"**Дата:** {context.user_data['book_date']}\n"
                f"**Стоимость:** {selected_route.get('price')} BYN\n\n"
                f"💡 Дальнейшие инструкции:\n"
                f"• Оплатите билет до даты отправления\n"
                f"• Приходите на посадку за 10-15 минут\n"
                f"• При посадке назовите номер бронирования\n\n"
                f"📱 Сохраните это сообщение!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎫 Мои бронирования", callback_data="my_bookings"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                ]])
            )
        else:
            error_msg = booking_result.get('error', 'Неизвестная ошибка')
            await query.edit_message_text(
                f"❌ **ОШИБКА БРОНИРОВАНИЯ**\n\n"
                f"**Причина:** {error_msg}\n\n"
                f"💡 Возможные решения:\n"
                f"• Проверьте баланс на сайте\n"
                f"• Попробуйте другой рейс\n"
                f"• Обратитесь в службу поддержки\n\n"
                f"🔄 Хотите попробовать еще раз?",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Попробовать снова", callback_data="book_route"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                ]])
            )
        
    except Exception as e:
        logger.error(f"Ошибка бронирования: {e}")
        await query.edit_message_text(
            f"❌ **КРИТИЧЕСКАЯ ОШИБКА**\n\n"
            f"Не удалось выполнить бронирование: {str(e)}\n\n"
            f"🔧 Обратитесь к администратору",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
            ]])
        )
    
    return ConversationHandler.END

# Добавить в conversation_handler:
# CallbackQueryHandler(handle_book_route, pattern="^book_route$"),
# CallbackQueryHandler(confirm_booking, pattern="^confirm_booking_\\d+$"),

# Добавить в states словарь:
# BOOK_ROUTE_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_route_from)],
# BOOK_ROUTE_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_route_to)],
# BOOK_ROUTE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_route_date)],
# BOOK_ROUTE_CONFIRM: [CallbackQueryHandler(confirm_booking, pattern="^confirm_booking_\\d+$")],
