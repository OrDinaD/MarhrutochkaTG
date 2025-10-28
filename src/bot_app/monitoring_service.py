"""Сервисные функции мониторинга маршрутов."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from telegram import InlineKeyboardButton
from telegram.ext import ContextTypes

from src.managers.user_manager import user_manager

from . import state
from .keyboards import create_webapp_keyboard
from .logging_utils import logger, safe_log_bot, safe_log_system
from .parser import init_parser, get_parser


def format_monitor_config(config: Dict[str, Any]) -> str:
    """Форматирует конфигурацию мониторинга для отображения пользователю."""
    direction_map = {
        "minsk_ostrovets": "Минск → Островец",
        "ostrovets_minsk": "Островец → Минск",
        "both": "Оба направления",
    }
    time_type_map = {
        "departure": "отправления",
        "arrival": "прибытия",
        "any": "любое",
    }
    parts = [
        f"📅 **Дата:** {config['date']}",
        f"🛣️ **Направление:** {direction_map.get(config['direction'], config['direction'])}",
        f"⏰ **Время:** {time_type_map.get(config['time_type'], config['time_type'])}",
        f"🕐 **Диапазон:** {config['time_range']}",
        "🔔 **Проверка:** каждые 5 минут",
    ]
    return "\n".join(parts)


async def restart_monitoring_scheduler() -> Dict[str, Any]:
    """Перезапускает планировщик мониторингов и восстанавливает задания."""
    if not state.job_queue:
        safe_log_system("Попытка перезапуска планировщика без job_queue", level="warning")
        return {"success": False, "reason": "job_queue_unavailable"}

    removed_jobs = 0
    failures: List[Dict[str, Any]] = []

    try:
        for job in list(state.job_queue.jobs()):
            job.schedule_removal()
            removed_jobs += 1
    except Exception as exc:  # pragma: no cover - защитное логирование
        safe_log_system(
            "Ошибка очистки job queue перед перезапуском",
            {"error": str(exc)},
            level="error",
        )
        logger.error("Ошибка при очистке job queue", exc_info=True)
        return {
            "success": False,
            "reason": "job_cleanup_failed",
            "error": str(exc),
        }

    await asyncio.sleep(0)

    state.job_queue.run_repeating(
        cleanup_stuck_callbacks,
        interval=30,
        first=10,
        name=state.CLEANUP_JOB_NAME,
    )

    restored_monitors = 0
    for user_id in list(user_manager.active_monitors.keys()):
        try:
            state.job_queue.run_repeating(
                check_routes_for_user,
                interval=300,
                first=10,
                name=f"monitor_{user_id}",
                data=user_id,
            )
            restored_monitors += 1
        except Exception as exc:  # pragma: no cover - логирование ошибок
            failure_info = {"user_id": user_id, "error": str(exc)}
            failures.append(failure_info)
            safe_log_bot(
                "Ошибка восстановления мониторинга при перезапуске планировщика",
                failure_info,
                level="error",
            )

    safe_log_system(
        "Планировщик мониторингов перезапущен",
        {
            "jobs_removed": removed_jobs,
            "monitors_restored": restored_monitors,
            "failures": len(failures),
        },
    )

    return {
        "success": len(failures) == 0,
        "jobs_removed": removed_jobs,
        "monitors_restored": restored_monitors,
        "failures": failures,
    }


async def trigger_bot_restart(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает приложение для последующего перезапуска."""
    restart_info = context.application.bot_data.setdefault("restart_info", {})
    restart_info.setdefault("pending", True)
    restart_info["triggered_at"] = datetime.now().isoformat()
    safe_log_system("Перезапуск бота инициирован", restart_info)
    context.application.stop_running()


async def check_routes_for_user(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверяет рейсы для конкретного пользователя."""
    user_id = context.job.data
    if user_id not in user_manager.active_monitors:
        return

    config = user_manager.active_monitors[user_id]

    try:
        parser = await init_parser()
        routes_data = await parser.get_all_routes(config["date"])
        if not routes_data.get("success", False):
            return

        suitable_routes = filter_routes_by_criteria(routes_data, config)
        if suitable_routes:
            await send_monitoring_notification(user_id, suitable_routes, config, context)
    except Exception as exc:  # pragma: no cover - логирование ошибок
        logger.error("Ошибка при проверке рейсов для пользователя %s: %s", user_id, exc)


def filter_routes_by_criteria(routes_data: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Фильтрует рейсы по критериям пользователя."""
    suitable_routes: List[Dict[str, Any]] = []
    routes_to_check: List[Dict[str, Any]] = []

    if config["direction"] in ["minsk_ostrovets", "both"]:
        routes_to_check.extend(routes_data.get("minsk_to_ostrovets", []))
    if config["direction"] in ["ostrovets_minsk", "both"]:
        routes_to_check.extend(routes_data.get("ostrovets_to_minsk", []))

    for route in routes_to_check:
        seats = route.get("available_seats", 0)
        if not isinstance(seats, int) or seats <= 0:
            continue

        if config["time_range"] not in {"any", "любое время"}:
            if not check_time_criteria(route, config):
                continue

        suitable_routes.append(route)

    return suitable_routes


def check_time_criteria(route: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Проверяет соответствие времени рейса критериям пользователя."""
    time_range = config["time_range"]
    time_type = config["time_type"]

    if time_type == "departure":
        route_time = route.get("departure_time", "")
    elif time_type == "arrival":
        route_time = route.get("arrival_time", "")
    else:
        return True

    if not route_time:
        return False

    try:
        route_hour, route_minute = map(int, route_time.split(":"))
        route_minutes = route_hour * 60 + route_minute

        if "-" in time_range:
            start_time, end_time = time_range.split("-")
            start_hour, start_minute = map(int, start_time.split(":"))
            end_hour, end_minute = map(int, end_time.split(":"))
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute

            if start_minutes <= end_minutes:
                return start_minutes <= route_minutes <= end_minutes
            return route_minutes >= start_minutes or route_minutes <= end_minutes
    except ValueError:
        return True

    return True


async def send_monitoring_notification(
    user_id: int,
    routes: List[Dict[str, Any]],
    config: Dict[str, Any],
    context: Optional[ContextTypes.DEFAULT_TYPE] = None,
) -> None:
    """Отправляет уведомление о найденных рейсах пользователю."""
    try:
        application = context.application if context else state.application
        bot = application.bot if application else None
        if not bot:
            logger.warning("Не удалось отправить уведомление: бот не инициализирован")
            return

        chat_id = config["chat_id"]
        direction_text = {
            "minsk_ostrovets": "Минск → Островец",
            "ostrovets_minsk": "Островец → Минск",
            "both": "в обоих направлениях",
        }.get(config["direction"], config["direction"])

        message_parts = [
            "🔔 **НАЙДЕНЫ ПОДХОДЯЩИЕ РЕЙСЫ!**",
            "",
            f"📅 **Дата:** {config['date']}",
            f"🛣️ **Направление:** {direction_text}",
            f"⏰ **Время:** {config['time_range']}",
            "",
        ]

        for idx, route in enumerate(routes[:5], 1):
            seats = route.get("available_seats", 0)
            emoji = "🔥" if seats <= 3 else "✅"
            direction = f"{route['from_city']} → {route['to_city']}"
            message_parts.append(f"**{idx}. {direction}**")
            message_parts.append(
                f"🚀 {route.get('departure_time')} → 🎯 {route.get('arrival_time')}"
            )
            message_parts.append(f"{emoji} **{seats} мест**")
            message_parts.append("")

        if len(routes) > 5:
            message_parts.append(f"... и еще {len(routes) - 5} рейсов")

        message_parts.append("\n📡 Мониторинг продолжается...")
        message = "\n".join(message_parts)

        keyboard_buttons = [
            [InlineKeyboardButton("🛑 Остановить мониторинг", callback_data="stop_monitoring")],
            [InlineKeyboardButton("📊 Мои мониторинги", callback_data="my_monitors")],
        ]
        webapp_keyboard = create_webapp_keyboard(
            config["direction"], config["date"], keyboard_buttons
        )

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=webapp_keyboard,
        )
    except Exception as exc:  # pragma: no cover - логирование ошибок
        logger.error("Ошибка отправки уведомления пользователю %s: %s", user_id, exc)


# Избегаем циклического импорта
from .callback_management import cleanup_stuck_callbacks  # noqa: E402


__all__ = [
    "check_routes_for_user",
    "check_time_criteria",
    "filter_routes_by_criteria",
    "format_monitor_config",
    "restart_monitoring_scheduler",
    "send_monitoring_notification",
    "trigger_bot_restart",
]
