import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import get_user_cities, set_primary_city, add_city
from keyboards import get_cities_keyboard, get_main_menu_keyboard

logger = logging.getLogger(__name__)

async def list_cities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    cities = await get_user_cities(user_id)
    p_id = next((c['id'] for c in cities if c['is_primary']), -1)
    await query.edit_message_text(
        "🏙️ <b>Города</b>", 
        reply_markup=get_cities_keyboard(cities, p_id), 
        parse_mode='HTML'
    )

async def set_primary_city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    cid = int(query.data.split("_")[2])
    
    await set_primary_city(user_id, cid)
    cities = await get_user_cities(user_id)
    city_name = next((c['city_name'] for c in cities if c['id'] == cid), "город")
    
    await query.edit_message_reply_markup(reply_markup=get_cities_keyboard(cities, cid))
    await query.answer(f"✅ Основной город: {city_name}")

async def ask_add_city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("🔎 Введите название города:")
    context.user_data['state'] = 'WAITING_CITY'
