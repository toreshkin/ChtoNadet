import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    get_user, update_user_field, get_notification_preferences, 
    update_notification_preference, update_user_timezone
)
from keyboards import (
    get_settings_keyboard, get_notification_settings_keyboard, 
    get_time_keyboard, get_sensitivity_keyboard,
    NOTIFICATION_PREFS, CHANGE_TIME, CHANGE_SENSITIVITY, CHANGE_NAME, CHANGE_TIMEZONE
)
from timezones import get_timezone_keyboard

logger = logging.getLogger(__name__)

async def settings_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    user = await get_user(user_id)
    await query.edit_message_text(
        "⚙️ <b>Настройки</b>", 
        reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), 
        parse_mode='HTML'
    )

async def notification_prefs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    prefs = await get_notification_preferences(user_id)
    await query.edit_message_text(
        "🔔 <b>Настройка уведомлений</b>", 
        reply_markup=get_notification_settings_keyboard(prefs), 
        parse_mode='HTML'
    )

async def toggle_notification_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    key = data.replace("toggle_", "")
    prefs = await get_notification_preferences(user_id)
    new_state = not prefs.get(key, True)
    
    await update_notification_preference(user_id, key, new_state)
    new_prefs = await get_notification_preferences(user_id)
    
    await query.edit_message_reply_markup(reply_markup=get_notification_settings_keyboard(new_prefs))
    status = "✅ Включено" if new_state else "❌ Выключено"
    await query.answer(status, show_alert=False)

async def sensitivity_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🌡️ <b>Чувствительность к температуре</b>\n\n"
        "😊 <b>Нормальный:</b> Стандарт\n"
        "❄️ <b>Мерзляк:</b> Советы потеплее\n"
        "🔥 <b>Жаркий:</b> Полегче",
        reply_markup=get_sensitivity_keyboard(),
        parse_mode='HTML'
    )

async def set_sensitivity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    m = {'sens_cold': 'cold_sensitive', 'sens_normal': 'normal', 'sens_hot': 'heat_sensitive'}
    await update_user_field(user_id, 'temperature_sensitivity', m[query.data])
    
    user = await get_user(user_id)
    await query.edit_message_text(
        "✅ Сохранено.\n⚙️ <b>Настройки</b>", 
        reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), 
        parse_mode='HTML'
    )

async def change_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("⏰ Введите время для утреннего прогноза (например, 08:30):")
    context.user_data['state'] = 'WAITING_TIME'

async def change_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("👤 Как мне к вам обращаться?")
    context.user_data['state'] = 'WAITING_NAME'
