import logging
import asyncio
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from core.bot import create_application
from core.logger import setup_logging
from config import LOG_LEVEL, ADMIN_ID

# Handlers
from handlers.start import start, ask_name, ask_timezone_handler, ask_location, cancel, ASK_NAME, ASK_TIMEZONE, ASK_LOCATION
from handlers.weather import weather_now_handler, weather_details_handler
from handlers.stats import show_stats_handler
from handlers.settings import (
    settings_main_handler, notification_prefs_handler, toggle_notification_handler,
    sensitivity_menu_handler, set_sensitivity_handler,
    change_time_handler, change_name_handler
)
from handlers.cities import (
    list_cities_handler, set_primary_city_handler, 
    ask_add_city_handler, remove_city_menu_handler, delete_city_handler
)
from handlers.menu import main_menu_callback_handler, help_handler
from handlers.text_input import handle_text_input

from scheduler import setup_scheduler
from database import init_db
from keyboards import (
    WEATHER_NOW, REFRESH_WEATHER, WEATHER_DETAILS, SETTINGS, 
    WEATHER_STATS, STATS, HELP, BACK_TO_MENU, NOTIFICATION_PREFS,
    LIST_CITIES, ADD_CITY, CHANGE_TIMEZONE, CHANGE_TIME, CHANGE_SENSITIVITY, CHANGE_NAME,
    REMOVE_CITY
)
from timezones import TIMEZONE_PREFIX, TIMEZONE_OTHER

# Initialize logging
logger = setup_logging(LOG_LEVEL)

async def post_init_logic(application):
    """Actions after application starts."""
    await init_db()
    setup_scheduler(application)
    logger.info("🚀 Bot is up and running!")

async def admin_command(update, context):
    """Admin only: show bot stats."""
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    from database import get_admin_stats
    stats = await get_admin_stats()
    msg = (
        f"📊 <b>Bot Admin Stats</b>\n\n"
        f"👥 Users: {stats['total_users']} ({stats['active_users']} active)\n"
        f"🏙 Cities: {stats['total_cities']}\n"
        f"📜 History: {stats['history_records']}"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

def main():
    application = create_application()

    # 1. Registration Flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_TIMEZONE: [CallbackQueryHandler(ask_timezone_handler)],
            ASK_LOCATION: [
                MessageHandler(filters.LOCATION, ask_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_location)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="registration_conv",
        persistent=False,
        allow_reentry=True  # Разрешаем перезапуск регистрации в любой момент
    )
    application.add_handler(conv_handler)

    # 2. Command Handlers
    application.add_handler(CommandHandler('weather', weather_now_handler))
    application.add_handler(CommandHandler('stats', show_stats_handler))
    application.add_handler(CommandHandler('settings', settings_main_handler))
    application.add_handler(CommandHandler('help', help_handler))
    application.add_handler(CommandHandler('admin', admin_command))

    # 3. Callback Query Handlers (Menus)
    application.add_handler(CallbackQueryHandler(weather_now_handler, pattern=f"^({WEATHER_NOW}|{REFRESH_WEATHER})$"))
    application.add_handler(CallbackQueryHandler(weather_details_handler, pattern=f"^{WEATHER_DETAILS}$"))
    application.add_handler(CallbackQueryHandler(show_stats_handler, pattern=f"^{WEATHER_STATS}|{STATS}$"))
    application.add_handler(CallbackQueryHandler(settings_main_handler, pattern=f"^{SETTINGS}$"))
    application.add_handler(CallbackQueryHandler(notification_prefs_handler, pattern=f"^{NOTIFICATION_PREFS}$"))
    application.add_handler(CallbackQueryHandler(toggle_notification_handler, pattern="^toggle_"))
    application.add_handler(CallbackQueryHandler(help_handler, pattern=f"^{HELP}$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback_handler, pattern=f"^{BACK_TO_MENU}$"))
    application.add_handler(CallbackQueryHandler(list_cities_handler, pattern=f"^{LIST_CITIES}$"))
    application.add_handler(CallbackQueryHandler(set_primary_city_handler, pattern="^view_city_"))
    
    # City Management
    application.add_handler(CallbackQueryHandler(ask_add_city_handler, pattern=f"^{ADD_CITY}$"))
    application.add_handler(CallbackQueryHandler(remove_city_menu_handler, pattern=f"^{REMOVE_CITY}$"))
    application.add_handler(CallbackQueryHandler(delete_city_handler, pattern="^delete_city_"))
    
    # Timezone & Settings
    application.add_handler(CallbackQueryHandler(ask_timezone_handler, pattern=f"^({TIMEZONE_PREFIX}|{TIMEZONE_OTHER}|TZ_BACK_MAIN|{CHANGE_TIMEZONE})"))
    application.add_handler(CallbackQueryHandler(sensitivity_menu_handler, pattern=f"^{CHANGE_SENSITIVITY}$"))
    application.add_handler(CallbackQueryHandler(set_sensitivity_handler, pattern="^sens_"))
    application.add_handler(CallbackQueryHandler(change_time_handler, pattern=f"^{CHANGE_TIME}$"))
    application.add_handler(CallbackQueryHandler(change_name_handler, pattern=f"^{CHANGE_NAME}$"))

    # 4. Text Handlers (Loose inputs like /weather Berlin or menu replies)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    # Post init
    application.post_init = post_init_logic

    # Start
    application.run_polling()

if __name__ == '__main__':
    main()
