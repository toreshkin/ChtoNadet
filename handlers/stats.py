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

    # generate_weekly_trend_graph returns a formatted text string (emoji graph)
    stats_text = generate_weekly_trend_graph(history)
    
    if not stats_text:
        msg = "⚠️ Не удалось сформировать статистику."
        if query: await query.message.reply_text(msg)
        else: await update.message.reply_text(msg)
        return
    
    caption = f"📊 <b>Статистика: {city['city_name']}</b>\n\n{stats_text}"
    
    if query:
        try:
            await query.edit_message_text(caption, parse_mode='HTML', reply_markup=get_back_keyboard())
        except Exception:
            await query.message.reply_text(caption, parse_mode='HTML', reply_markup=get_back_keyboard())
    else:
        await update.message.reply_text(caption, parse_mode='HTML')

