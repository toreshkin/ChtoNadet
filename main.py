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
from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY
from database import (
    init_db, upsert_user, get_user, update_user_field, 
    add_city, get_user_cities, remove_city, set_primary_city, 
    get_primary_city, get_weekly_stats, 
    update_user_timezone, get_users_needing_timezone_init, mark_timezone_initialized,
    get_notification_preferences, update_notification_preference, 
    save_weather_snapshot, get_weather_comparison, create_snapshots_table,
    save_wardrobe_item, get_users_with_null_timezone, create_wardrobe_table
)
from weather import get_coordinates, get_current_weather, get_forecast, get_uv_index, get_air_quality
from scheduler import setup_scheduler
from analytics import (
    generate_comparison_text, generate_weekly_trend_graph, suggest_activities, 
    analyze_best_activity_time, format_uv_recommendation, format_aqi_message,
    get_smart_insight
)
from recommendations import get_weather_emoji, get_clothing_advice
from ai_analysis import init_gemini, analyze_clothing_photo, generate_clothing_recommendation

from keyboards import (
    get_main_menu_keyboard, get_settings_keyboard, get_cities_keyboard,
    get_sensitivity_keyboard, get_time_keyboard, get_back_keyboard,
    get_weather_action_buttons, get_notification_settings_keyboard,
    get_photo_analysis_buttons,
    WEATHER_NOW, SETTINGS, STATS, HELP, BACK_TO_MENU,
    CHANGE_CITY, LIST_CITIES, ADD_CITY, REMOVE_CITY,
    CHANGE_TIME, CHANGE_SENSITIVITY, CHANGE_NAME, CHANGE_TIMEZONE,
    TOGGLE_NOTIFICATIONS, NOTIFICATION_PREFS,
    REFRESH_WEATHER, WEATHER_DETAILS, WEATHER_STATS,
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

# --- HELPER: Message Generation ---
async def generate_weather_message_content(user_id, city_data):
    if not city_data: return "У вас нет добавленных городов."
    
    lat, lon = city_data['latitude'], city_data['longitude']
    city_name = city_data['city_name']
    
    # 1. Fetch Data
    forecast = await get_forecast(lat=lat, lon=lon) # Includes hourly for today
    current = await get_current_weather(lat=lat, lon=lon) # Realtime
    uv = await get_uv_index(city_name)
    aqi_data = await get_air_quality(city_name)
    user = await get_user(user_id)
    
    if not current or not forecast: return "Не удалось получить данные о погоде."

    # 2. Comparison
    comp_text = ""
    comp_data = await get_weather_comparison(user_id, city_name)
    if comp_data:
        comp_text = generate_comparison_text(current['main']['temp'], comp_data['temp'])
        comp_text = f"<i>{comp_text}</i>"
    
    # Save NEW snapshot
    try:
        await save_weather_snapshot(user_id, city_name, current['main']['temp'], current['weather'][0]['description'])
    except: pass

    # 3. Format Strings
    temp = current['main']['temp']
    feels = current['main']['feels_like']
    cond = current['weather'][0]['description']
    cond = cond.capitalize()
    emoji_icon = get_weather_emoji(current['weather'][0]['id'])
    
    # Details
    wind = current['wind']['speed'] * 3.6 # km/h
    humid = current['main']['humidity']
    aqi_msg = format_aqi_message(aqi_data.get('aqi_val', 0)) if aqi_data else ""
    uv_msg = f"☀️ <b>УФ-индекс:</b> {uv}"
    
    # Hourly & Forecast (simplified view)
    list_data = forecast.get('list', [])
    forecast_text = "<b>📅 Прогноз на день:</b>\n"
    periods = [("09:00", "🌅 Утро"), ("15:00", "☀️ День"), ("21:00", "🌇 Вечер")]
    found_p = False
    
    for time_target, label in periods:
        for item in list_data:
            t = item['dt_txt'].split(' ')[1][:5]
            if t == time_target:
                p_temp = item['main']['temp']
                p_cond = item['weather'][0]['description']
                forecast_text += f"{label}: {p_temp:+.0f}°C • {p_cond}\n"
                found_p = True
                break
    if not found_p: forecast_text += "Данные обновляются...\n"

    # Best activity time
    activity_time = analyze_best_activity_time(list_data)
    
    # Recommendations
    sens = user.get('temperature_sensitivity', 'normal')
    name = user.get('user_name', 'друг')
    clothing = get_clothing_advice(temp, current['weather'][0]['id'], wind/3.6, sens, name)
    rec_text = f"<b>👔 Рекомендации:</b>\n{clothing.replace(f'{name}, советую: ', '')}"
    
    # Insight
    smart_text = get_smart_insight({'temp': temp, 'humidity': humid, 'wind': wind/3.6, 'condition_code': current['weather'][0]['id']})
    if smart_text: smart_text = f"💡 {smart_text}\n"

    # UX Layout
    msg = f"""
<b>{emoji_icon} Погода в {city_name}</b>

<b>Сейчас:</b> {temp:+.0f}°C (ощущается {feels:+.0f}°C)
{cond}
{comp_text}

━━━━━━━━━━━━━━━
<b>📊 Детали:</b>
💨 Ветер: {wind:.1f} км/ч
💧 Влажность: {humid}%
{uv_msg}
{aqi_msg}

━━━━━━━━━━━━━━━
{forecast_text}
━━━━━━━━━━━━━━━
{activity_time}

━━━━━━━━━━━━━━━
{rec_text}

{smart_text}
"""
    return msg

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
        f"Приятно познакомиться, {name}! 😊\n\n🌍 Теперь выберите ваш часовой пояс:",
        reply_markup=get_timezone_keyboard()
    )
    return ASK_TIMEZONE

async def ask_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == TIMEZONE_OTHER:
        await query.edit_message_text("🌎 Выберите регион:", reply_markup=get_extended_timezone_keyboard())
        return ASK_TIMEZONE
    if data == "TZ_BACK_MAIN":
        await query.edit_message_text("🌍 Выберите ваш часовой пояс:", reply_markup=get_timezone_keyboard())
        return ASK_TIMEZONE
    if data.startswith(TIMEZONE_PREFIX):
        tz = data.replace(TIMEZONE_PREFIX, "")
        context.user_data['temp_timezone'] = tz
        d = get_timezone_display_name(tz)
        await query.edit_message_text(f"✅ Выбран: {d}")
        await query.message.reply_text("📍 Отправьте свою геолокацию или название города.")
        return ASK_LOCATION
    return ASK_TIMEZONE

async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    lat, lon, city_name = None, None, None
    
    if msg.location:
        lat, lon = msg.location.latitude, msg.location.longitude
        city_name = "GPS Локация"
        try:
             # Reverse geo via WeatherAPI if we wanted real name
             pass
        except: pass
    else:
        city_name = msg.text
        coords = await get_coordinates(city_name)
        if not coords:
            await msg.reply_text("❌ Город не найден. Попробуйте еще раз.")
            return ASK_LOCATION
        lat, lon = coords
    
    name = context.user_data.get('temp_name', 'друг')
    tz = context.user_data.get('temp_timezone', 'Europe/Moscow')
    
    await upsert_user(user.id, user.username, user_name=name, timezone=tz)
    await add_city(user.id, city_name, lat, lon, is_primary=True)
    
    await msg.reply_text(
        f"✅ Настройка завершена!\nЯ буду присылать прогнозы в 07:00.\n\n📸 Отправьте мне фото одежды, чтобы узнать, подходит ли она на сегодня!",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

# --- PHOTO HANDLER ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Сначала нажмите /start")
        return

    loading_msg = await update.message.reply_text("📸 Анализирую одежду... ⏳")
    
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        
        clothing_data = await analyze_clothing_photo(bytes(photo_bytes))
        
        if not clothing_data.get('success'):
            await loading_msg.edit_text("❌ Не удалось проанализировать фото.")
            return

        # Get weather
        city = await get_primary_city(user_id)
        if not city:
             await loading_msg.edit_text("❌ Нет города. Настройте город в меню.")
             return
             
        current = await get_current_weather(city['latitude'], city['longitude'])
        
        message = generate_clothing_recommendation(clothing_data, current, user['user_name'])
        
        await loading_msg.edit_text(
            message,
            reply_markup=get_photo_analysis_buttons(photo.file_id),
            parse_mode='HTML'
        )
        
        # Cache data temporarily for saving? 
        context.user_data[f"clothing_{photo.file_id}"] = clothing_data

    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await loading_msg.edit_text("❌ Ошибка сервиса. Попробуйте позже.")

# --- MENUS ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == WEATHER_NOW or data == REFRESH_WEATHER:
        city = await get_primary_city(user_id)
        msg = await generate_weather_message_content(user_id, city)
        try:
             await query.edit_message_text(msg, parse_mode='HTML', reply_markup=get_weather_action_buttons())
        except:
             await query.message.reply_text(msg, parse_mode='HTML', reply_markup=get_weather_action_buttons())

    elif data == WEATHER_DETAILS:
        city = await get_primary_city(user_id)
        uv = await get_uv_index(city['city_name'])
        rec = format_uv_recommendation(uv)
        await query.message.reply_text(f"📊 <b>Подробности</b>\n\n{rec}", parse_mode='HTML')

    elif data == WEATHER_STATS or data == STATS:
        await show_stats(query, user_id)

    elif data == SETTINGS:
        user = await get_user(user_id)
        await query.edit_message_text("⚙️ <b>Настройки</b>", reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), parse_mode='HTML')

    elif data == NOTIFICATION_PREFS:
        prefs = await get_notification_preferences(user_id)
        await query.edit_message_text("🔔 <b>Настройка уведомлений</b>", reply_markup=get_notification_settings_keyboard(prefs), parse_mode='HTML')

    elif data.startswith("toggle_"):
        key = data.replace("toggle_", "")
        prefs = await get_notification_preferences(user_id)
        curr = prefs.get(key, 1)
        await update_notification_preference(user_id, key, not curr)
        prefs = await get_notification_preferences(user_id)
        await query.edit_message_reply_markup(reply_markup=get_notification_settings_keyboard(prefs))

    elif data == HELP:
        await query.edit_message_text("ℹ️ <b>Помощь</b>\n\nПросто отправьте фото одежды для анализа!", reply_markup=get_back_keyboard(), parse_mode='HTML')

    elif data == BACK_TO_MENU:
        try:
            await query.edit_message_text("📱 <b>Главное меню</b>", reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
        except:
             await query.message.reply_text("📱 <b>Главное меню</b>", reply_markup=get_main_menu_keyboard(), parse_mode='HTML')

    elif data == LIST_CITIES:
        cities = await get_user_cities(user_id)
        p_id = next((c['id'] for c in cities if c['is_primary']), -1)
        await query.edit_message_text("🏙️ <b>Города</b>", reply_markup=get_cities_keyboard(cities, p_id), parse_mode='HTML')

    elif data.startswith("view_city_"):
        cid = int(data.split("_")[2])
        await set_primary_city(user_id, cid)
        cities = await get_user_cities(user_id)
        await query.edit_message_reply_markup(reply_markup=get_cities_keyboard(cities, cid))

    elif data == ADD_CITY:
        await query.message.reply_text("Введите название города:")
        context.user_data['state'] = 'WAITING_CITY'

    elif data == REMOVE_CITY:
        await query.answer("Нажмите на город...") 

    elif data == CHANGE_TIMEZONE:
        await query.edit_message_text("🌍 Выберите:", reply_markup=get_timezone_keyboard())

    elif data == TIMEZONE_OTHER:
        await query.edit_message_text("🌎 Регион:", reply_markup=get_extended_timezone_keyboard())

    elif data == "TZ_BACK_MAIN":
         await query.edit_message_text("🌍 Часовой пояс:", reply_markup=get_timezone_keyboard())

    elif data.startswith(TIMEZONE_PREFIX):
        tz = data.replace(TIMEZONE_PREFIX, "")
        await update_user_timezone(user_id, tz)
        user = await get_user(user_id) 
        await query.edit_message_text("✅ Часовой пояс сохранен.\n⚙️ <b>Настройки</b>", reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), parse_mode='HTML')

    elif data == CHANGE_TIME:
        await query.edit_message_text("🕐 Время:", reply_markup=get_time_keyboard())

    elif data == CHANGE_SENSITIVITY:
        await query.edit_message_text("🌡️ Чувствительность:", reply_markup=get_sensitivity_keyboard())

    elif data.startswith("sens_"):
        m = {'sens_cold': 'cold_sensitive', 'sens_normal': 'normal', 'sens_hot': 'heat_sensitive'}
        await update_user_field(user_id, 'temperature_sensitivity', m[data])
        user = await get_user(user_id)
        await query.edit_message_text("✅ Сохранено.\n⚙️ <b>Настройки</b>", reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), parse_mode='HTML')

    elif data.startswith("time_"):
        t = data.split("_")[1]
        if t == 'custom':
            await query.message.reply_text("Введите время (ЧЧ:ММ):")
            context.user_data['state'] = 'WAITING_TIME'
        else:
            await update_user_field(user_id, 'notification_time', t)
            user = await get_user(user_id)
            await query.edit_message_text(f"✅ Время: {t}\n⚙️ <b>Настройки</b>", reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), parse_mode='HTML')

    elif data == CHANGE_NAME:
        await query.message.reply_text("Введите имя:")
        context.user_data['state'] = 'WAITING_NAME'

    elif data.startswith("save_clothing_"):
        fid = data.replace("save_clothing_", "")
        c_data = context.user_data.get(f"clothing_{fid}")
        if c_data:
            await save_wardrobe_item(user_id, fid, c_data)
            await query.answer("✅ Сохранено в гардероб!")
        else:
            await query.answer("❌ Данные устарели")
            
    elif data == "analyze_again":
        await query.message.reply_text("📸 Отправьте новое фото.")

async def show_stats(query, user_id):
    city = await get_primary_city(user_id)
    if not city: return
    stats = await get_weekly_stats(user_id, city['city_name'])
    if not stats:
        await query.edit_message_text("Нет статистики. Она появится через пару дней.", reply_markup=get_back_keyboard())
        return
    
    graph = generate_weekly_trend_graph(stats)
    await query.edit_message_text(graph, reply_markup=get_back_keyboard(), parse_mode='HTML')

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state')
    
    if state == 'WAITING_TIME':
        try:
             import datetime
             datetime.datetime.strptime(msg, "%H:%M")
             await update_user_field(user_id, 'notification_time', msg)
             await update.message.reply_text(f"✅ Время: {msg}")
        except: await update.message.reply_text("❌ Неверный формат.")
        context.user_data['state'] = None
    elif state == 'WAITING_CITY':
        coords = await get_coordinates(msg)
        if coords:
            await add_city(user_id, msg, coords[0], coords[1])
            await update.message.reply_text(f"✅ Город {msg} добавлен!")
        else: await update.message.reply_text("❌ Не найдено.")
        context.user_data['state'] = None
    elif state == 'WAITING_NAME':
        await update_user_field(user_id, 'user_name', msg)
        await update.message.reply_text(f"✅ Имя: {msg}")
        context.user_data['state'] = None
    else:
        await update.message.reply_text("Меню:", reply_markup=get_main_menu_keyboard())

async def post_init(application: ApplicationBuilder):
    """
    Initialize database and run one-time migrations
    DO NOT re-prompt users for timezone on every restart
    """
    await init_db()
    
    # Init Gemini
    init_gemini(GEMINI_API_KEY)

    # Only initialize timezone for truly new users or users with NULL timezone
    users_needing_tz = await get_users_with_null_timezone()
    
    for user_id in users_needing_tz:
        try:
            await application.bot.send_message(
                user_id,
                "🌍 Пожалуйста, выберите ваш часовой пояс:",
                reply_markup=get_timezone_keyboard()
            )
            await mark_timezone_initialized(user_id)
        except: pass

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Token error")
        return

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    setup_scheduler(application)

    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_TIMEZONE: [CallbackQueryHandler(ask_timezone_handler)],
            ASK_LOCATION: [MessageHandler(filters.TEXT | filters.LOCATION, ask_location)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv)
    application.add_handler(CommandHandler("menu", lambda u,c: u.message.reply_text("Меню:", reply_markup=get_main_menu_keyboard())))
    application.add_handler(CallbackQueryHandler(menu_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    print("Bot running...")
    application.run_polling()

if __name__ == '__main__':
    main()
