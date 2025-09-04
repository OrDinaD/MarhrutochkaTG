#!/usr/bin/env python3
"""
Роутер для обработки callback queries в Telegram боте
Оптимизирует обработку callback'ов вместо большой функции с множеством if/elif
"""
from typing import Dict, Callable, Awaitable, Optional
from telegram import Update
from telegram.ext import ContextTypes


class CallbackRouter:
    """Роутер для обработки callback queries"""
    
    def __init__(self):
        self.routes: Dict[str, Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable]] = {}
        self.prefix_routes: Dict[str, Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable]] = {}
    
    def route(self, callback_data: str):
        """Декоратор для регистрации обработчика точного совпадения callback_data"""
        def decorator(func):
            self.routes[callback_data] = func
            return func
        return decorator
    
    def route_prefix(self, prefix: str):
        """Декоратор для регистрации обработчика по префиксу callback_data"""
        def decorator(func):
            self.prefix_routes[prefix] = func
            return func
        return decorator
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
        """Главный обработчик callback queries"""
        query = update.callback_query
        
        if not query or not query.data:
            return None
            
        callback_data = query.data
        
        # Проверяем точные совпадения
        if callback_data in self.routes:
            return await self.routes[callback_data](update, context)
        
        # Проверяем префиксы
        for prefix, handler in self.prefix_routes.items():
            if callback_data.startswith(prefix):
                return await handler(update, context)
        
        # Если обработчик не найден
        return None
    
    def get_routes_info(self) -> str:
        """Возвращает информацию о зарегистрированных маршрутах"""
        routes_info = []
        routes_info.append("📊 **Зарегистрированные маршруты:**\n")
        
        if self.routes:
            routes_info.append("**Точные совпадения:**")
            for route in sorted(self.routes.keys()):
                routes_info.append(f"• `{route}`")
            routes_info.append("")
        
        if self.prefix_routes:
            routes_info.append("**Префиксы:**")
            for prefix in sorted(self.prefix_routes.keys()):
                routes_info.append(f"• `{prefix}*`")
        
        return "\n".join(routes_info)


# Создаем глобальный экземпляр роутера
callback_router = CallbackRouter()
