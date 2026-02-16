"""
Хендлер регистрации новых пользователей.
Упрощенный и надежный флоу с подробным логированием.
"""
import logging
import html
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from database import upsert_user, add_city, get_user, get_primary_city, update_user_timezone
from services.weather_service import generate_weather_message_content
from weather import get_coordinates
from streak import update_streak, get_streak_message
from keyboards import get_main_reply_keyboard, get_weather_action_buttons, get_timezone_keyboard, get_extended_timezone_keyboard
from timezones import get_timezone_display_name, TIMEZONE_PREFIX, TIMEZONE_OTHER

logger = logging.getLogger(__name__)

# States
ASK_NAME, ASK_TIMEZONE, ASK_LOCATION = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало регистрации или приветствие существующего пользователя."""
    try:
        # СБРОС состояние при каждом /start
        context.user_data.clear()
        
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        
        logger.info(f"👤 User {user_id} ({username}) запустил /start")
        
        # Проверяем, зарегистрирован ли пользователь
        user = await get_user(user_id)
        
        if user:
            logger.info(f"✅ User {user_id} уже зарегистрирован")
            await update_streak(user_id)
            await update.message.reply_text(
                f"👋 С возвращением, {user['user_name']}!\n\n"
                f"Используйте меню ниже для получения прогноза или настроек.",
                reply_markup=get_main_reply_keyboard()
            )
            return ConversationHandler.END
        
        # Новый пользователь - начинаем регистрацию
        logger.info(f"🆕 Начало регистрации для user {user_id}")
        await update.message.reply_text(
            "👋 <b>Привет! Я погодный помощник.</b>\n\n"
            "Я помогу вам одеваться по погоде и получать актуальные прогнозы.\n\n"
            "Как мне к вам обращаться?",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        return ASK_NAME
        
    except Exception as e:
        logger.error(f"❌ Ошибка в start для user {update.effective_user.id}: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте еще раз: /start"
        )
        return ConversationHandler.END


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени."""
    try:
        # Очистка и валидация имени
        name = html.escape(update.message.text.strip())
        user_id = update.effective_user.id
        
        logger.info(f"📝 User {user_id} ввел имя: {name}")
        
        # Валидация
        if len(name) < 2:
            await update.message.reply_text("❌ Имя слишком короткое. Введите хотя бы 2 символа:")
            return ASK_NAME
            
        if len(name) > 50:
            await update.message.reply_text("❌ Имя слишком длинное (макс. 50 символов). Попробуйте короче:")
            return ASK_NAME
        
        # Сохраняем имя во временные данные
        context.user_data['temp_name'] = name
        
        # Переход к выбору часового пояса
        await update.message.reply_text(
            f"Приятно познакомиться, {name}! 😊\n\n"
            f"🌍 <b>Выберите ваш часовой пояс:</b>",
            reply_markup=get_timezone_keyboard(),
            parse_mode='HTML'
        )
        return ASK_TIMEZONE
        
    except Exception as e:
        logger.error(f"❌ Ошибка в ask_name для user {update.effective_user.id}: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте ввести имя еще раз:"
        )
        return ASK_NAME


async def ask_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора часового пояса."""
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = update.effective_user.id
        
        logger.info(f"🌍 User {user_id} выбрал timezone callback: {data}")
        
        # Показать расширенный список
        if data == TIMEZONE_OTHER:
            await query.edit_message_text(
                "🌎 <b>Выберите регион:</b>",
                reply_markup=get_extended_timezone_keyboard(),
                parse_mode='HTML'
            )
            return ASK_TIMEZONE
        
        # Вернуться к основному списку
        if data == "TZ_BACK_MAIN" or data == "change_timezone":
            await query.edit_message_text(
                "🌍 <b>Выберите ваш часовой пояс:</b>",
                reply_markup=get_timezone_keyboard(),
                parse_mode='HTML'
            )
            return ASK_TIMEZONE
        
        # Выбран конкретный часовой пояс
        if data.startswith(TIMEZONE_PREFIX):
            tz = data.replace(TIMEZONE_PREFIX, "")
            tz_display = get_timezone_display_name(tz)
            logger.info(f"✅ User {user_id} выбрал timezone: {tz}")

            # Проверяем, это регистрация или настройки (по наличию temp_name)
            if context.user_data.get('temp_name'):
                # РЕГИСТРАЦИЯ
                context.user_data['temp_timezone'] = tz
                await query.edit_message_text(f"✅ <b>Выбран:</b> {tz_display}", parse_mode='HTML')
                await query.message.reply_text(
                    "📍 <b>Последний шаг!</b>\n\n"
                    "Отправьте название вашего города (например, «Москва») или "
                    "нажмите кнопку для отправки геолокации:",
                    reply_markup=ReplyKeyboardMarkup(
                        [[KeyboardButton("📍 Отправить мою локацию", request_location=True)]],
                        resize_keyboard=True
                    ),
                    parse_mode='HTML'
                )
                return ASK_LOCATION
            else:
                # НАСТРОЙКИ (смена таймзоны)
                await update_user_timezone(user_id, tz)
                await query.edit_message_text(
                    f"✅ <b>Часовой пояс обновлен:</b>\n{tz_display}\n\n"
                    "Теперь уведомления будут приходить по этому времени.",
                    parse_mode='HTML'
                )
                return ConversationHandler.END
        
        return ASK_TIMEZONE
        
    except Exception as e:
        logger.error(f"❌ Ошибка в ask_timezone_handler для user {update.effective_user.id}: {e}", exc_info=True)
        await query.message.reply_text(
            "⚠️ Произошла ошибка. Начните заново: /start"
        )
        return ConversationHandler.END


async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода локации и завершение регистрации."""
    try:
        user = update.effective_user
        msg = update.message
        user_id = user.id
        lat, lon, city_name = None, None, None
        
        logger.info(f"📍 User {user_id} отправил локацию")
        
        # Обработка GPS локации
        if msg.location:
            lat, lon = msg.location.latitude, msg.location.longitude
            city_name = f"GPS ({lat:.2f}, {lon:.2f})"
            logger.info(f"✅ User {user_id} использовал GPS: {lat}, {lon}")
        
        # Обработка текстового ввода города
        else:
            city_name = msg.text.strip()
            logger.info(f"🔍 User {user_id} ввел город: {city_name}")
            
            # Получаем координаты города
            try:
                coords = await get_coordinates(city_name)
                if not coords:
                    logger.warning(f"❌ Город не найден: {city_name}")
                    await msg.reply_text(
                        f"❌ Не удалось найти город «{city_name}».\n\n"
                        f"Попробуйте:\n"
                        f"• Указать другое название (Moskva, Moscow)\n"
                        f"• Использовать английское название\n"
                        f"• Отправить GPS-локацию кнопкой ниже",
                        reply_markup=ReplyKeyboardMarkup(
                            [[KeyboardButton("📍 Отправить мою локацию", request_location=True)]],
                            resize_keyboard=True
                        )
                    )
                    return ASK_LOCATION
                lat, lon = coords
                logger.info(f"✅ Координаты найдены для {city_name}: {lat}, {lon}")
            except Exception as e:
                logger.error(f"❌ Ошибка при поиске города {city_name}: {e}", exc_info=True)
                await msg.reply_text(
                    "⚠️ <b>Сервис геолокации временно недоступен.</b>\n\n"
                    "Попробуйте через минуту или отправьте GPS-локацию:",
                    reply_markup=ReplyKeyboardMarkup(
                        [[KeyboardButton("📍 Отправить мою локацию", request_location=True)]],
                        resize_keyboard=True
                    ),
                    parse_mode='HTML'
                )
                return ASK_LOCATION
        
        # Получаем сохраненные данные
        name = context.user_data.get('temp_name', 'друг')
        tz = context.user_data.get('temp_timezone', 'Europe/Moscow')
        
        logger.info(f"💾 Сохранение данных пользователя {user_id}: name={name}, tz={tz}, city={city_name}")
        
        # Сохраняем пользователя в БД
        try:
            await upsert_user(user_id, user.username, user_name=name, timezone=tz)
            await add_city(user_id, city_name, lat, lon, is_primary=True)
            logger.info(f"✅ User {user_id} успешно сохранен в БД")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в БД для user {user_id}: {e}", exc_info=True)
            await msg.reply_text(
                "⚠️ Произошла ошибка при сохранении данных.\n"
                "Попробуйте начать заново: /start",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        # Получаем данные пользователя для отображения
        user_data = await get_user(user_id)
        notif_time = user_data.get('notification_time', '07:00')
        
        # Отправляем приветственное сообщение
        await msg.reply_text(
            f"✅ <b>Настройка завершена!</b>\n\n"
            f"🔔 <b>Утренний прогноз:</b> {notif_time}\n"
            f"<i>(изменить можно в ⚙️ Настройках)</i>\n\n"
            f"🌤 <b>Смотрите погоду прямо сейчас:</b> ⬇️",
            reply_markup=get_main_reply_keyboard(),
            parse_mode='HTML'
        )
        
        # Получаем и отправляем прогноз погоды
        try:
            city_data = await get_primary_city(user_id)
            weather_msg = await generate_weather_message_content(user_id, city_data)
            current_streak, best_streak, is_new_record = await update_streak(user_id)
            streak_msg = get_streak_message(current_streak, is_new_record)
            
            await msg.reply_text(
                f"{weather_msg}\n\n{streak_msg}",
                parse_mode='HTML',
                reply_markup=get_weather_action_buttons()
            )
            logger.info(f"🎉 Регистрация user {user_id} завершена успешно!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении погоды для user {user_id}: {e}", exc_info=True)
            await msg.reply_text(
                "⚠️ Погода временно недоступна.\n"
                "Используйте кнопку «🌤 Погода сейчас» в меню.",
                parse_mode='HTML'
            )
        
        # Очищаем временные данные
        context.user_data.clear()
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в ask_location для user {update.effective_user.id}: {e}", exc_info=True)
        await msg.reply_text(
            "⚠️ Произошла критическая ошибка.\n"
            "Начните регистрацию заново: /start",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена регистрации."""
    user_id = update.effective_user.id
    logger.info(f"❌ User {user_id} отменил регистрацию")
    
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Настройка отменена.\n\n"
        "Используйте /start, чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
