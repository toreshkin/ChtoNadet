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
    if text == "🌤 Погода" or text == WEATHER_NOW:
        return await weather_now_handler(update, context)
        
    if text == "⚙️ Настройки" or text == SETTINGS:
        user = await get_user(user_id)
        if not user:
             await update.message.reply_text("Пожалуйста, зарегистрируйтесь через /start")
             return
        await update.message.reply_text(
            "⚙️ <b>Настройки</b>", 
            reply_markup=get_settings_keyboard(user.get('is_active', True), user.get('alerts_enabled', True)), 
            parse_mode='HTML'
        )
        return
        
    if text == "📊 Статистика" or text == STATS:
        return await show_stats_handler(update, context)
        
    if text == "ℹ️ Помощь" or text == HELP:
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
        text = text.strip()
        if ":" in text and len(text) == 5:
            try:
                h, m = map(int, text.split(':'))
                if 0 <= h <= 23 and 0 <= m <= 59:
                    await update_user_field(user_id, 'notification_time', text)
                    context.user_data['state'] = None
                    user = await get_user(user_id)
                    await update.message.reply_text(f"✅ Время уведомлений: {text}", reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), parse_mode='HTML')
                else:
                    await update.message.reply_text("❌ Неверное время. Часы 00-23, минуты 00-59. Пример: 08:30")
            except ValueError:
                await update.message.reply_text("❌ Неверный формат. Нужно ЧЧ:ММ (например, 08:30):")
        else:
            await update.message.reply_text("❌ Неверный формат. Нужно ЧЧ:ММ (например, 08:30):")

    elif state == 'WAITING_NAME':
        name = text.strip()
        if 2 <= len(name) <= 50:
            await update_user_field(user_id, 'user_name', name)
            context.user_data['state'] = None
            user = await get_user(user_id)
            await update.message.reply_text(f"✅ Теперь я зову вас: {name}", reply_markup=get_settings_keyboard(user['is_active'], user['alerts_enabled']), parse_mode='HTML')
        elif len(name) < 2:
            await update.message.reply_text("❌ Имя слишком короткое (минимум 2 символа).")
        else:
            await update.message.reply_text("❌ Слишком длинное имя (максимум 50 символов).")
    else:
        # Unrecognized text — give a helpful response
        await update.message.reply_text(
            "🤔 Не совсем понял. Используйте кнопки меню ниже или команды:\n"
            "/weather — погода\n"
            "/settings — настройки\n"
            "/help — помощь"
        )
