import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import get_primary_city, get_user
from services.weather_service import generate_weather_message_content
from streak import update_streak, get_streak_message
from keyboards import get_weather_action_buttons, WEATHER_NOW, REFRESH_WEATHER, WEATHER_DETAILS
from weather import get_uv_index
from analytics import format_uv_recommendation

logger = logging.getLogger(__name__)

async def weather_now_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query:
        await query.answer("⏳ Загружаю погоду...", show_alert=False)
    
    city = await get_primary_city(user_id)
    if not city:
        await (query.message.reply_text if query else update.message.reply_text)("У вас нет добавленных городов. Используйте /start.")
        return

    current_streak, best_streak, is_new_record = await update_streak(user_id)
    streak_msg = get_streak_message(current_streak, is_new_record)
    
    weather_text = await generate_weather_message_content(user_id, city)
    full_msg = f"{weather_text}\n\n{streak_msg}"
    
    if query:
        try:
            await query.edit_message_text(full_msg, parse_mode='HTML', reply_markup=get_weather_action_buttons())
        except:
            await query.message.reply_text(full_msg, parse_mode='HTML', reply_markup=get_weather_action_buttons())
    else:
        await update.message.reply_text(full_msg, parse_mode='HTML', reply_markup=get_weather_action_buttons())

async def weather_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    city = await get_primary_city(user_id)
    uv = await get_uv_index(city['city_name'])
    rec = format_uv_recommendation(uv)
    await query.message.reply_text(f"📊 <b>Подробности</b>\n\n{rec}", parse_mode='HTML')
