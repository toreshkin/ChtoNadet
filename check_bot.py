#!/usr/bin/env python
"""
Скрипт для проверки запуска бота без фактического запуска.
Проверяет все импорты и инициализацию.
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_imports():
    """Проверка всех критичных импортов."""
    try:
        logger.info("🔍 Проверка импортов...")
        
        # Core imports
        from telegram.ext import Application
        logger.info("✅ telegram.ext - OK")
        
        # Config
        from config import TELEGRAM_BOT_TOKEN, WEATHERAPI_KEY
        logger.info("✅ config - OK")
        
        # Database
        from database import init_db, get_user
        logger.info("✅ database - OK")
        
        # Keyboards
        from keyboards import (
            get_main_menu_keyboard, 
            get_weather_action_buttons,
            get_timezone_keyboard,
            get_extended_timezone_keyboard,
            REMOVE_CITY, CHANGE_TIME, CHANGE_NAME
        )
        logger.info("✅ keyboards - OK")
        
        # Handlers
        from handlers.start import start, ask_name, ask_timezone_handler, ask_location, cancel
        logger.info("✅ handlers.start - OK")
        
        from handlers.weather import weather_now_handler
        logger.info("✅ handlers.weather - OK")
        
        from handlers.settings import (
            settings_main_handler, 
            change_time_handler, 
            change_name_handler
        )
        logger.info("✅ handlers.settings - OK")
        
        from handlers.cities import (
            remove_city_menu_handler, 
            delete_city_handler
        )
        logger.info("✅ handlers.cities - OK")
        
        # Weather services
        from weather import get_coordinates, get_current_weather, get_forecast
        logger.info("✅ weather - OK")
        
        # Other services
        from streak import update_streak, get_streak_message, get_streak_info
        logger.info("✅ streak - OK")
        
        from scheduler import setup_scheduler
        logger.info("✅ scheduler - OK")
        
        logger.info("✅ Все импорты успешны!")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        return False

def check_env():
    """Проверка переменных окружения."""
    try:
        logger.info("🔍 Проверка переменных окружения...")
        from config import TELEGRAM_BOT_TOKEN, WEATHERAPI_KEY
        
        if not TELEGRAM_BOT_TOKEN or len(TELEGRAM_BOT_TOKEN) < 20:
            logger.error("❌ TELEGRAM_BOT_TOKEN не установлен или невалидный")
            return False
        logger.info("✅ TELEGRAM_BOT_TOKEN - OK")
        
        if not WEATHERAPI_KEY or len(WEATHERAPI_KEY) < 10:
            logger.error("❌ WEATHERAPI_KEY не установлен или невалидный")
            return False
        logger.info("✅ WEATHERAPI_KEY - OK")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки env: {e}")
        return False

def check_database():
    """Проверка доступности базы данных."""
    try:
        logger.info("🔍 Проверка базы данных...")
        import os
        from config import DATABASE_PATH
        
        if os.path.exists(DATABASE_PATH):
            logger.info(f"✅ База данных найдена: {DATABASE_PATH}")
            return True
        else:
            logger.warning(f"⚠️ База данных не найдена: {DATABASE_PATH}")
            logger.info("   Будет создана при первом запуске")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки БД: {e}")
        return False

def main():
    """Основная функция проверки."""
    logger.info("=" * 50)
    logger.info("🤖 Проверка готовности бота к запуску")
    logger.info("=" * 50)
    
    checks = [
        ("Импорты", check_imports()),
        ("Переменные окружения", check_env()),
        ("База данных", check_database()),
    ]
    
    logger.info("\n" + "=" * 50)
    logger.info("📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
    logger.info("=" * 50)
    
    all_ok = True
    for name, result in checks:
        status = "✅ OK" if result else "❌ FAIL"
        logger.info(f"{name}: {status}")
        if not result:
            all_ok = False
    
    logger.info("=" * 50)
    
    if all_ok:
        logger.info("🎉 Все проверки пройдены! Бот готов к запуску.")
        logger.info("   Запустите: python main.py")
        return 0
    else:
        logger.error("⚠️ Некоторые проверки не прошли. Исправьте ошибки перед запуском.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
