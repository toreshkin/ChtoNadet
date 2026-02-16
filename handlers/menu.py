import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards import get_main_menu_keyboard, get_back_keyboard

logger = logging.getLogger(__name__)

async def main_menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text("📱 <b>Главное меню</b>", reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    except:
        await query.message.reply_text("📱 <b>Главное меню</b>", reply_markup=get_main_menu_keyboard(), parse_mode='HTML')

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    help_text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "🌤 <b>Погода сейчас:</b>\n"
        "Актуальный прогноз с температурой, ветром, UV-индексом и AQI.\n\n"
        "📊 <b>Статистика:</b>\n"
        "Тренды за неделю.\n\n"
        "⚙️ <b>Настройки:</b>\n"
        "Управление городами, временем и чувствительностью.\n\n"
        "👔 <b>Рекомендации:</b>\n"
        "Советы по одежде на основе погоды."
    )
    
    if query:
        await query.edit_message_text(help_text, reply_markup=get_back_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_text(help_text, parse_mode='HTML')
