import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import TELEGRAM_BOT_TOKEN
from database import (
    init_db, upsert_user, get_user, update_user_field, 
    add_city, get_user_cities, remove_city, set_primary_city, 
    get_primary_city, get_weekly_stats, 
    update_user_timezone, get_users_needing_timezone_init, mark_timezone_initialized
)
from weather import get_coordinates, get_current_weather, get_forecast
from recommendations import format_daily_forecast, get_weather_emoji
from scheduler import send_daily_notifications, save_daily_history_job as history_job
from keyboards import (
    get_main_menu_keyboard, get_settings_keyboard, get_cities_keyboard,
    get_sensitivity_keyboard, get_time_keyboard, get_back_keyboard,
    WEATHER_NOW, SETTINGS, STATS, HELP, BACK_TO_MENU,
    CHANGE_CITY, LIST_CITIES, ADD_CITY, REMOVE_CITY,
    CHANGE_TIME, CHANGE_SENSITIVITY, CHANGE_NAME, CHANGE_TIMEZONE,
    TOGGLE_NOTIFICATIONS, TOGGLE_ALERTS, 
    SENSITIVITY_COLD, SENSITIVITY_NORMAL, SENSITIVITY_HOT
)
from timezones import (
    get_timezone_keyboard, get_extended_timezone_keyboard, get_timezone_display_name,
    TIMEZONE_PREFIX, TIMEZONE_OTHER, COMMON_TIMEZONES
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for Conversation
ASK_NAME, ASK_TIMEZONE, ASK_LOCATION = range(3)
ADD_CITY_NAME = range(1)
CUSTOM_TIME = range(1)
INPUT_NAME = range(1)

# --- START FLOW ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я помогу вам одеваться по погоде.\nКак мне к вам обращаться?")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if len(name) > 50:
        await update.message.reply_text("Имя слишком длинное. Попробуйте короче:")
        return ASK_NAME
    
    context.user_data['temp_name'] = name
    await update.message.reply_text(
        f"Приятно познакомиться, {name}! 😊\n\n🌍 Теперь выберите ваш часовой пояс, чтобы я присылал уведомления вовремя:",
        reply_markup=get_timezone_keyboard()
    )
    return ASK_TIMEZONE

async def ask_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == TIMEZONE_OTHER:
        await query.edit_message_text(
            "🌎 Выберите регион из списка ниже:",
            reply_markup=get_extended_timezone_keyboard()
        )
        return ASK_TIMEZONE
        
    if data == "TZ_BACK_MAIN":
        await query.edit_message_text(
            "🌍 Выберите ваш часовой пояс:",
            reply_markup=get_timezone_keyboard()
        )
        return ASK_TIMEZONE
        
    if data.startswith(TIMEZONE_PREFIX):
        timezone = data.replace(TIMEZONE_PREFIX, "")
        context.user_data['temp_timezone'] = timezone
        
        display_name = get_timezone_display_name(timezone)
        await query.edit_message_text(f"✅ Выбран часовой пояс: {display_name}")
        await query.message.reply_text("📍 Теперь отправьте свою геолокацию или напишите название города.")
        return ASK_LOCATION
    
    return ASK_TIMEZONE

async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    
    lat, lon, city_name = None, None, None
    
    if msg.location:
        lat, lon = msg.location.latitude, msg.location.longitude
        # We should reverse geocode technically, but for now generic name or from weather API
        # Let's try to get city name from weather check later, or currently just "Мое местоположение"
        # Since we use weather API, we can fetch name from it if we wanted strictness.
        # But let's just use "GPS" for internal name if text not provided.
        city_name = "GPS Локация"
        # Better: Quick check to weather API to get name? 
        # For speed, we just accept it.
    else:
        city_name = msg.text
        coords = await get_coordinates(city_name)
        if not coords:
            await msg.reply_text("❌ Не удалось найти город. Попробуйте еще раз.")
            return ASK_LOCATION
        lat, lon = coords
    
    name = context.user_data.get('temp_name', 'друг')
    timezone = context.user_data.get('temp_timezone', 'Europe/Moscow')
    
    # Register/Update user
    await upsert_user(user.id, user.username, user_name=name, timezone=timezone)
    
    # Add city
    await add_city(user.id, city_name, lat, lon, is_primary=True)
    
    await msg.reply_text(
        f"✅ Отлично, {name}! Город {city_name} добавлен.\nЯ буду присылать прогнозы каждое утро в 07:00.",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

# --- MENUS and CALLBACKS ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == WEATHER_NOW:
        await show_weather_now(query, user_id)
    elif data == SETTINGS:
        user = await get_user(user_id)
        await query.edit_message_text(
            "⚙️ <b>Настройки</b>", 
            reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']),
            parse_mode='HTML'
        )
    elif data == STATS:
        await show_stats(query, user_id)
    elif data == HELP:
        await query.edit_message_text(
            "ℹ️ <b>Помощь</b>\n\nЯ бот-метеоролог. Я могу:\n- Показывать погоду сейчас\n- Присылать ежедневные прогнозы\n- Давать советы по одежде\n- Вести статистику\n\nИспользуйте меню для навигации.", 
            reply_markup=get_back_keyboard(),
            parse_mode='HTML'
        )
    elif data == BACK_TO_MENU:
        await query.edit_message_text("📱 <b>Главное меню</b>", reply_markup=get_main_menu_keyboard(), parse_mode='HTML')

    # Settings Submenu
    elif data == LIST_CITIES:
        cities = await get_user_cities(user_id)
        # Find primary id
        primary_id = next((c['id'] for c in cities if c['is_primary']), -1)
        await query.edit_message_text("🏙️ <b>Ваши города</b>\nНажмите на город, чтобы сделать его основным.", reply_markup=get_cities_keyboard(cities, primary_id), parse_mode='HTML')
    
    elif data == CHANGE_TIMEZONE:
        user = await get_user(user_id)
        current_tz = user.get('timezone', 'Europe/Moscow')
        display = get_timezone_display_name(current_tz)
        await query.edit_message_text(f"🌍 Текущий: {display}\nВыберите новый часовой пояс:", reply_markup=get_timezone_keyboard())

    elif data == TIMEZONE_OTHER:
         await query.edit_message_text("🌎 Выберите регион:", reply_markup=get_extended_timezone_keyboard())

    elif data == "TZ_BACK_MAIN":
         await query.edit_message_text("🌍 Выберите ваш часовой пояс:", reply_markup=get_timezone_keyboard())

    elif data.startswith(TIMEZONE_PREFIX):
        new_tz = data.replace(TIMEZONE_PREFIX, "")
        await update_user_timezone(user_id, new_tz)
        display = get_timezone_display_name(new_tz)
        
        # Get user settings to return to keyboard
        user = await get_user(user_id)
        
        await query.answer(f"✅ Часовой пояс изменен на {display}")
        await query.edit_message_text(
             f"✅ Часовой пояс изменен на {display}\n\n⚙️ <b>Настройки</b>",
             reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']),
             parse_mode='HTML'
        )

    elif data == CHANGE_TIME:
        await query.edit_message_text("🕐 Выберите время получения уведомлений:", reply_markup=get_time_keyboard())
    
    elif data == CHANGE_SENSITIVITY:
         await query.edit_message_text("🌡️ Как вы ощущаете холод?", reply_markup=get_sensitivity_keyboard())

    elif data == TOGGLE_NOTIFICATIONS:
        user = await get_user(user_id)
        new_val = not user['is_active']
        await update_user_field(user_id, 'is_active', 1 if new_val else 0)
        await query.edit_message_text("⚙️ <b>Настройки</b>", reply_markup=get_settings_keyboard(new_val, user['alerts_enabled']), parse_mode='HTML')
        
    elif data == TOGGLE_ALERTS:
        user = await get_user(user_id)
        new_val = not user['alerts_enabled']
        await update_user_field(user_id, 'alerts_enabled', 1 if new_val else 0)
        await query.edit_message_text("⚙️ <b>Настройки</b>", reply_markup=get_settings_keyboard(user['is_active'], new_val), parse_mode='HTML')
    
    elif data == ADD_CITY:
        await query.message.reply_text("Введите название нового города:")
        return # Client side needs to know state? Not pure callback. 
        # Since we can't easily switch to ConversationHandler state from CallbackQuery without workaround, 
        # we often use a separate command or use `context.user_data['state']` if using a global message handler.
        # But here we used ConversationHandler for start.
        # Let's start a city_add conversation via text message prompt.
        # Limitation: CallbackQuery cannot arbitrary start a ConversationHandler unless entry points match.
        # Workaround: Send message "Enter city name..." and user types it. We need a general MessageHandler to catch it if state is set.
        
    elif data.startswith("view_city_"):
        city_id = int(data.split("_")[2])
        await set_primary_city(user_id, city_id)
        await query.answer("✅ Основной город изменен!")
        # Refresh list
        cities = await get_user_cities(user_id)
        await query.edit_message_reply_markup(reply_markup=get_cities_keyboard(cities, city_id))

    elif data == REMOVE_CITY:
        # Show list to remove? Simplified: click city to set primary. 
        # Implementing removal UI inside inline keyboard is distinct.
        # For now, let's just toggle back to settings.
        await query.answer("Для удаления используйте меню городов (пока не реализовано UI удаление)")
        
    elif data.startswith("sens_"):
        map_val = {'sens_cold': 'cold_sensitive', 'sens_normal': 'normal', 'sens_hot': 'heat_sensitive'}
        await update_user_field(user_id, 'temperature_sensitivity', map_val[data])
        await query.answer("✅ Чувствительность обновлена!")
        await query.edit_message_text("⚙️ <b>Настройки</b>", reply_markup=get_settings_keyboard(True, True), parse_mode='HTML') # refresh status? User status logic needed

    elif data.startswith("time_"):
         t = data.split("_")[1]
         if t == 'custom':
             await query.message.reply_text("Напишите время в формате ЧЧ:ММ (например 14:30)")
             # Again, dealing with text input.
         else:
             await update_user_field(user_id, 'notification_time', t)
             await query.answer(f"✅ Время установлено: {t}")
             await query.edit_message_text("⚙️ <b>Настройки</b>", reply_markup=get_settings_keyboard(True, True), parse_mode='HTML')

# --- HELPERS ---
async def show_weather_now(query, user_id):
    city = await get_primary_city(user_id)
    if not city:
        await query.answer("Нет городов!")
        return
        
    forecast = await get_forecast(lat=city['latitude'], lon=city['longitude'])
    user = await get_user(user_id)
    
    if forecast:
        text = format_daily_forecast(forecast, user['temperature_sensitivity'], city['city_name'], user['user_name'])
        # Edit message or send new? If forecast is long, better send new.
        await query.message.reply_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
    else:
        await query.answer("Ошибка получения погоды.")

async def show_stats(query, user_id):
    city = await get_primary_city(user_id)
    if not city: return
    
    stats = await get_weekly_stats(user_id, city['city_name'])
    if not stats:
        await query.edit_message_text("📊 Пока нет статистики. Она появится через пару дней активного использования.", reply_markup=get_back_keyboard())
        return
        
    # Build Stats Text
    lines = [f"📊 <b>Статистика: {city['city_name']}</b>\n"]
    for s in stats:
        date_nice = s['date'] # ideally format "25 янв"
        lines.append(f"{date_nice}: {s['temp_min']:.0f}°...{s['temp_max']:.0f}°C, {s['condition']}")
        
    await query.edit_message_text("\n".join(lines), reply_markup=get_back_keyboard(), parse_mode='HTML')

# --- ADD CITY CONVERSATION ---
async def add_city_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This must be triggered by a command or similar if we can't chain from callback easily without tweaks.
    # We will use command /addcity or just rely on the 'ADD_CITY' callback prompting user, 
    # but we need a handler that listens to text.
    pass

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """General handler for text inputs when not in explicit conversation."""
    msg = update.message.text
    user_id = update.effective_user.id
    
    # Check if we are waiting for custom time?
    # Simple state management via user_data
    state = context.user_data.get('state')
    
    if state == 'WAITING_TIME':
        # Validate and set time
        try:
            import datetime
            datetime.datetime.strptime(msg, "%H:%M")
            await update_user_field(user_id, 'notification_time', msg)
            await update.message.reply_text(f"✅ Время установлено: {msg}")
            context.user_data['state'] = None
        except:
             await update.message.reply_text("❌ Неверный формат. ЧЧ:ММ")
             
    elif state == 'WAITING_CITY':
        coords = await get_coordinates(msg)
        if coords:
            await add_city(user_id, msg, coords[0], coords[1])
            await update.message.reply_text(f"✅ Город {msg} добавлен!")
            context.user_data['state'] = None
        else:
             await update.message.reply_text("❌ Город не найден.")
             
    elif state == 'WAITING_NAME':
        await update_user_field(user_id, 'user_name', msg)
        await update.message.reply_text(f"✅ Имя изменено на {msg}")
        context.user_data['state'] = None
    
    else:
        # Default fallback
        await update.message.reply_text("Используйте меню:", reply_markup=get_main_menu_keyboard())

# --- Callback query for inputs ---
async def detailed_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == CHANGE_NAME:
        await query.message.reply_text("Введите новое имя:")
        context.user_data['state'] = 'WAITING_NAME'
        await query.answer()

    elif data == ADD_CITY:
        await query.message.reply_text("Введите название города:")
        context.user_data['state'] = 'WAITING_CITY'
        await query.answer()
        
    elif data == 'time_custom':
        await query.message.reply_text("Введите время (ЧЧ:ММ):")
        context.user_data['state'] = 'WAITING_TIME'
        await query.answer()
        
    else:
        await menu_handler(update, context)


async def post_init(application: ApplicationBuilder):
    await init_db()
    
    # Timezone migration broadcast
    users_to_init = await get_users_needing_timezone_init()
    if users_to_init:
        logger.info(f"Sending timezone init message to {len(users_to_init)} users...")
        for uid in users_to_init:
            try:
                await application.bot.send_message(
                    uid,
                    "🕐 <b>Обновление бота!</b>\n\nТеперь вы можете выбрать свой часовой пояс для точного времени уведомлений.\nПожалуйста, выберите ваш часовой пояс:",
                    reply_markup=get_timezone_keyboard(),
                    parse_mode='HTML'
                )
                await mark_timezone_initialized(uid)
            except Exception as e:
                logger.error(f"Failed to send timezone init to {uid}: {e}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        return

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Registration Flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_TIMEZONE: [CallbackQueryHandler(ask_timezone_handler)],
            ASK_LOCATION: [MessageHandler(filters.TEXT | filters.LOCATION, ask_location)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    
    # Generic Commands
    application.add_handler(CommandHandler("menu", lambda u,c: u.message.reply_text("Меню:", reply_markup=get_main_menu_keyboard())))
    
    # Callback Query Handler
    application.add_handler(CallbackQueryHandler(detailed_callback_handler))

    # Text Handler for states (Time, Name, City)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    # Scheduler
    job_queue = application.job_queue
    job_queue.run_repeating(send_daily_notifications, interval=60, first=10)
    job_queue.run_repeating(history_job, interval=86400, first=80000) # Simple periodicity

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
