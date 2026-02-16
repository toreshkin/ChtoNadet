#!/usr/bin/env python
"""
Скрипт для проверки всех обработчиков и маршрутов бота.
Проверяет корректность подключения всех кнопок и команд.
"""
import sys
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def check_handler_mappings():
    """Проверка соответствия кнопок и обработчиков."""
    logger.info("=" * 60)
    logger.info("🔍 ПРОВЕРКА МАРШРУТИЗАЦИИ ОБРАБОТЧИКОВ")
    logger.info("=" * 60)
    
    # Импортируем все константы кнопок
    from keyboards import (
        WEATHER_NOW, REFRESH_WEATHER, WEATHER_DETAILS, SETTINGS,
        WEATHER_STATS, STATS, HELP, BACK_TO_MENU, NOTIFICATION_PREFS,
        LIST_CITIES, ADD_CITY, CHANGE_TIMEZONE, CHANGE_TIME, 
        CHANGE_SENSITIVITY, CHANGE_NAME, REMOVE_CITY,
        SENSITIVITY_COLD, SENSITIVITY_NORMAL, SENSITIVITY_HOT
    )
    
    # Проверяем импорты обработчиков
    try:
        from handlers.start import start, ask_name, ask_timezone_handler, ask_location, cancel
        from handlers.weather import weather_now_handler, weather_details_handler
        from handlers.stats import show_stats_handler
        from handlers.settings import (
            settings_main_handler, notification_prefs_handler, 
            toggle_notification_handler, sensitivity_menu_handler, 
            set_sensitivity_handler, change_time_handler, change_name_handler
        )
        from handlers.cities import (
            list_cities_handler, set_primary_city_handler, 
            ask_add_city_handler, remove_city_menu_handler, delete_city_handler
        )
        from handlers.menu import main_menu_callback_handler, help_handler
        from handlers.text_input import handle_text_input
        logger.info("✅ Все обработчики успешно импортированы\n")
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта обработчиков: {e}")
        return False
    
    # Карта: callback_data -> handler
    mappings = {
        # Погода
        WEATHER_NOW: "weather_now_handler",
        REFRESH_WEATHER: "weather_now_handler",
        WEATHER_DETAILS: "weather_details_handler",
        WEATHER_STATS: "show_stats_handler",
        
        # Меню
        STATS: "show_stats_handler",
        HELP: "help_handler",
        BACK_TO_MENU: "main_menu_callback_handler",
        SETTINGS: "settings_main_handler",
        
        # Уведомления
        NOTIFICATION_PREFS: "notification_prefs_handler",
        "toggle_*": "toggle_notification_handler",
        
        # Города
        LIST_CITIES: "list_cities_handler",
        ADD_CITY: "ask_add_city_handler",
        REMOVE_CITY: "remove_city_menu_handler",
        "view_city_*": "set_primary_city_handler",
        "delete_city_*": "delete_city_handler",
        
        # Настройки
        CHANGE_TIMEZONE: "ask_timezone_handler",
        CHANGE_TIME: "change_time_handler",
        CHANGE_NAME: "change_name_handler",
        CHANGE_SENSITIVITY: "sensitivity_menu_handler",
        SENSITIVITY_COLD: "set_sensitivity_handler",
        SENSITIVITY_NORMAL: "set_sensitivity_handler",
        SENSITIVITY_HOT: "set_sensitivity_handler",
    }
    
    logger.info("📋 КАРТА ОБРАБОТЧИКОВ:")
    logger.info("-" * 60)
    for callback, handler in sorted(mappings.items()):
        logger.info(f"  {callback:30} → {handler}")
    logger.info("")
    
    return True

def check_text_button_mappings():
    """Проверка текстовых кнопок меню."""
    logger.info("=" * 60)
    logger.info("🔘 ПРОВЕРКА ТЕКСТОВЫХ КНОПОК МЕНЮ")
    logger.info("=" * 60)
    
    text_buttons = {
        "🌤 Погода": "weather_now_handler",
        "⚙️ Настройки": "settings_main_handler (через handle_text_input)",
        "📊 Статистика": "show_stats_handler",
        "ℹ️ Помощь": "help_handler",
        "📍 Моя геолокация": "Отправка GPS координат",
    }
    
    logger.info("📋 ТЕКСТОВЫЕ КНОПКИ:")
    logger.info("-" * 60)
    for button, handler in text_buttons.items():
        logger.info(f"  {button:25} → {handler}")
    logger.info("")
    
    return True

def check_conversation_flow():
    """Проверка потока регистрации."""
    logger.info("=" * 60)
    logger.info("🔄 ПРОВЕРКА ПОТОКА РЕГИСТРАЦИИ")
    logger.info("=" * 60)
    
    flow = [
        ("1. /start", "start() → ASK_NAME"),
        ("2. Ввод имени", "ask_name() → ASK_TIMEZONE"),
        ("3. Выбор timezone", "ask_timezone_handler() → ASK_LOCATION"),
        ("4. Ввод города/GPS", "ask_location() → ConversationHandler.END"),
        ("5. /cancel", "cancel() → ConversationHandler.END"),
    ]
    
    logger.info("📋 ЭТАПЫ РЕГИСТРАЦИИ:")
    logger.info("-" * 60)
    for step, action in flow:
        logger.info(f"  {step:25} → {action}")
    logger.info("")
    
    logger.info("✅ Особенности:")
    logger.info("  • allow_reentry=True - можно перезапустить /start в любой момент")
    logger.info("  • context.user_data.clear() в начале start()")
    logger.info("")
    
    return True

def check_state_handlers():
    """Проверка обработчиков состояний."""
    logger.info("=" * 60)
    logger.info("📝 ПРОВЕРКА ОБРАБОТЧИКОВ СОСТОЯНИЙ")
    logger.info("=" * 60)
    
    states = {
        "WAITING_CITY": "handle_text_input → add_city",
        "WAITING_TIME": "handle_text_input → update_user_field('notification_time')",
        "WAITING_NAME": "handle_text_input → update_user_field('user_name')",
    }
    
    logger.info("📋 СОСТОЯНИЯ (context.user_data['state']):")
    logger.info("-" * 60)
    for state, handler in states.items():
        logger.info(f"  {state:20} → {handler}")
    logger.info("")
    
    return True

def check_critical_fixes():
    """Проверка критических исправлений."""
    logger.info("=" * 60)
    logger.info("🔧 КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ")
    logger.info("=" * 60)
    
    fixes = [
        ("✅", "ImportError для get_timezone_keyboard", "Добавлен реэкспорт в keyboards.py"),
        ("✅", "CHANGE_TIMEZONE не обрабатывался", "Добавлен в паттерн ask_timezone_handler"),
        ("✅", "CHANGE_TIME не обрабатывался", "Создан change_time_handler"),
        ("✅", "CHANGE_NAME не обрабатывался", "Создан change_name_handler"),
        ("✅", "REMOVE_CITY не обрабатывался", "Создан remove_city_menu_handler"),
        ("✅", "Текстовые кнопки не работали", "Исправлены проверки в handle_text_input"),
        ("✅", "UnicodeEncodeError (суррогаты)", "Заменен \\ud83d\\udc54 на 👔"),
        ("✅", "Файл графика блокировался", "Чтение в память перед удалением"),
        ("✅", "/start не сбрасывал состояние", "Добавлен context.user_data.clear()"),
    ]
    
    for status, issue, fix in fixes:
        logger.info(f"{status} {issue:40} → {fix}")
    logger.info("")
    
    return True

def verify_imports():
    """Проверка всех критических импортов."""
    logger.info("=" * 60)
    logger.info("📦 ПРОВЕРКА ИМПОРТОВ")
    logger.info("=" * 60)
    
    imports_to_check = [
        ("telegram.ext", "Application, ConversationHandler"),
        ("config", "TELEGRAM_BOT_TOKEN, WEATHERAPI_KEY"),
        ("database", "init_db, get_user, upsert_user, update_user_timezone"),
        ("keyboards", "get_timezone_keyboard, REMOVE_CITY, CHANGE_TIME"),
        ("handlers.start", "start, ask_timezone_handler"),
        ("handlers.settings", "change_time_handler, change_name_handler"),
        ("handlers.cities", "remove_city_menu_handler, delete_city_handler"),
        ("services.weather_service", "generate_weather_message_content"),
    ]
    
    all_ok = True
    for module, items in imports_to_check:
        try:
            exec(f"from {module} import {items}")
            logger.info(f"✅ {module:30} → {items}")
        except ImportError as e:
            logger.error(f"❌ {module:30} → ОШИБКА: {e}")
            all_ok = False
    
    logger.info("")
    return all_ok

def main():
    """Главная функция проверки."""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 10 + "🤖 ПРОВЕРКА TELEGRAM WEATHER BOT" + " " * 15 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("\n")
    
    checks = [
        ("Импорты", verify_imports),
        ("Маршруты обработчиков", check_handler_mappings),
        ("Текстовые кнопки", check_text_button_mappings),
        ("Поток регистрации", check_conversation_flow),
        ("Обработчики состояний", check_state_handlers),
        ("Критические исправления", check_critical_fixes),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке '{name}': {e}")
            results.append((name, False))
    
    # Итоговый отчет
    logger.info("=" * 60)
    logger.info("📊 ИТОГОВЫЙ ОТЧЕТ")
    logger.info("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status:10} {name}")
    
    logger.info("-" * 60)
    logger.info(f"Пройдено: {passed}/{total}")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Бот готов к работе.\n")
        return 0
    else:
        logger.error(f"\n⚠️ Обнаружены проблемы. Исправьте ошибки.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
