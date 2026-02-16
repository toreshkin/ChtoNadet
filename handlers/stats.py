import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from database import get_primary_city, get_weekly_stats
from analytics import generate_weekly_trend_graph
from keyboards import get_back_keyboard

logger = logging.getLogger(__name__)

async def show_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if query:
        await query.answer("⏳ Собираю статистику...")
    
    city = await get_primary_city(user_id)
    if not city:
        msg = "Сначала добавьте город."
        if query: await query.message.reply_text(msg)
        else: await update.message.reply_text(msg)
        return

    history = await get_weekly_stats(user_id, city['city_name'])
    
    if len(history) < 2:
        msg = "⚠️ Недостаточно данных для статистики. Подождите пару дней."
        if query: await query.message.reply_text(msg)
        else: await update.message.reply_text(msg)
        return

    graph_path = generate_weekly_trend_graph(history, city['city_name'])
    
    caption = f"📊 <b>Статистика: {city['city_name']}</b>\nТренды температуры за неделю."
    
    if query:
        await query.message.reply_photo(photo=open(graph_path, 'rb'), caption=caption, parse_mode='HTML', reply_markup=get_back_keyboard())
    else:
        await update.message.reply_photo(photo=open(graph_path, 'rb'), caption=caption, parse_mode='HTML')
        
    # Cleanup graph
    if os.path.exists(graph_path):
        os.remove(graph_path)
