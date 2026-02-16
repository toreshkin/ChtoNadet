from telegram import Update
from telegram.ext import ContextTypes
from database import update_user_field, add_city, get_user, upsert_user
from weather import get_coordinates
from keyboards import get_settings_keyboard, get_main_menu_keyboard, WEATHER_NOW, SETTINGS, STATS, HELP
from handlers.weather import weather_now_handler
from handlers.stats import show_stats_handler
from handlers.menu import help_handler

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get('state')
    
    # 1. Route main menu reply keyboard buttons
    if text == WEATHER_NOW:
        return await weather_now_handler(update, context)
    if text == SETTINGS:
        user = await get_user(user_id)
        await update.message.reply_text("⚙️ <b>Настройки</b>", reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), parse_mode='HTML')
        return
    if text in [STATS, "📊 Статистика"]:
        return await show_stats_handler(update, context)
    if text == HELP:
        return await help_handler(update, context)
    
    # 2. Handle Conversation States (Text Inputs)
    if state == 'WAITING_CITY':
        coords = await get_coordinates(text)
        if not coords:
            await update.message.reply_text("❌ Город не найден. Попробуйте еще раз:")
            return
        lat, lon = coords
        await add_city(user_id, text, lat, lon)
        context.user_data['state'] = None
        await update.message.reply_text(f"✅ Город <b>{text}</b> добавлен!", parse_mode='HTML', reply_markup=get_main_menu_keyboard())

    elif state == 'WAITING_TIME':
        if ":" in text and len(text) == 5:
            await update_user_field(user_id, 'notification_time', text)
            context.user_data['state'] = None
            user = await get_user(user_id)
            await update.message.reply_text(f"✅ Время уведомлений: {text}", reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Неверный формат. Нужно ЧЧ:ММ (например, 08:30):")

    elif state == 'WAITING_NAME':
        if len(text) < 50:
            await update_user_field(user_id, 'user_name', text)
            context.user_data['state'] = None
            user = await get_user(user_id)
            await update.message.reply_text(f"✅ Теперь я зову вас: {text}", reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Слишком длинное имя.")
