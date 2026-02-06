"""
Smart notification system background jobs.
"""
import logging
import datetime
import pytz
from telegram.ext import ContextTypes
from database import get_all_active_users, get_primary_city, get_notification_preferences, update_notification_preference
from weather import get_forecast, check_rain_in_next_hours, get_uv_index, get_air_quality, get_severe_weather_alerts

logger = logging.getLogger(__name__)

async def check_rain_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Run every hour."""
    try:
        users = await get_all_active_users()
        utc_now = datetime.datetime.now(pytz.utc)
        
        for user in users:
            uid = user['user_id']
            prefs = await get_notification_preferences(uid)
            if not prefs['rain_alerts']: continue
            
            # Rate limit check: don't spam. Check last_rain_alert
            last_alert = prefs['last_rain_alert']
            if last_alert:
                # Parse and check if < 6 hours ago
                pass # Implementation simplified: assume we rely on strict checks or db update
                
            city_data = await get_primary_city(uid)
            if not city_data: continue
            
            rain_info = await check_rain_in_next_hours(city_data['city_name'], hours=2)
            if rain_info and rain_info['will_rain']:
                # Send alert
                msg = (f"☔ <b>{user['user_name']}, через час ожидается дождь!</b>\n"
                       f"🕐 Начало: ~{rain_info['start_time']}\n"
                       f"💧 Интенсивность: {rain_info['intensity']}\n"
                       f"Не забудьте взять зонт! ☂️")
                
                try:
                    await context.bot.send_message(uid, msg, parse_mode='HTML')
                    # Update last alert time
                    await update_notification_preference(uid, 'last_rain_alert', utc_now.isoformat())
                except Exception as e:
                    logger.error(f"Failed to send rain alert to {uid}: {e}")

    except Exception as e:
        logger.error(f"Error in rain alerts: {e}")

async def check_uv_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Run daily at specific time (e.g. 7 AM user time via scheduler filter/logic)."""
    # Scheduler calls this.
    try:
        users = await get_all_active_users()
        # For simplicity, we iterate all users. But ideally pass 'users_in_timezone'.
        
        for user in users:
            try:
                uid = user['user_id']
                prefs = await get_notification_preferences(uid)
                if not prefs['uv_alerts']: continue
                
                city_data = await get_primary_city(uid)
                if not city_data: continue
                
                uv = await get_uv_index(city_data['city_name'])
                if uv >= 6:
                    msg = (f"☀️ <b>{user['user_name']}, сегодня высокий УФ-индекс ({uv})!</b>\n"
                           "🧴 Не забудьте крем SPF 30+ и очки.")
                    try:
                        await context.bot.send_message(uid, msg, parse_mode='HTML')
                    except Exception as send_err:
                        logger.error(f"Failed to send UV alert to {uid}: {send_err}")
            except Exception as user_err:
                logger.error(f"Error processing UV alert for user {user.get('user_id')}: {user_err}")

    except Exception as e:
        logger.error(f"Critical error in UV alerts job: {e}")

async def check_air_quality_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Run every 6 hours."""
    try:
        users = await get_all_active_users()
        for user in users:
            try:
                uid = user['user_id']
                prefs = await get_notification_preferences(uid)
                if not prefs['air_quality_alerts']: continue
                
                city_data = await get_primary_city(uid)
                if not city_data: continue
                
                aqi_data = await get_air_quality(city_data['city_name'])
                # We computed 'aqi_val' in weather.py
                aqi_val = aqi_data.get('aqi_val', 0) if aqi_data else 0
                
                if aqi_val > 100:
                    msg = (f"🔴 <b>Внимание! Плохое качество воздуха.</b>\n"
                           f"AQI: {aqi_val}\n"
                           "Рекомендуем надеть маску или ограничить время на улице.")
                    await context.bot.send_message(uid, msg, parse_mode='HTML')
            except Exception as user_err:
                logger.error(f"Error processing AQI alert for user {user.get('user_id')}: {user_err}")

    except Exception as e:
        logger.error(f"Critical error in AQI alerts job: {e}")

async def check_severe_weather(context: ContextTypes.DEFAULT_TYPE):
    """Run every hour."""
    try:
        users = await get_all_active_users()
        for user in users:
            try:
                uid = user['user_id']
                prefs = await get_notification_preferences(uid)
                if not prefs['severe_weather_alerts']: continue
                
                city_data = await get_primary_city(uid)
                if not city_data: continue
                
                alerts = await get_severe_weather_alerts(city_data['city_name'])
                if alerts:
                    for alert in alerts:
                        # Check if recently sent?
                        # For MVP, send first one.
                        event = alert.get('event', 'Опасность')
                        desc = alert.get('desc', '')
                        msg = (f"⚠️ <b>ШТОРМОВОЕ ПРЕДУПРЕЖДЕНИЕ: {event}</b>\n\n"
                               f"{desc[:200]}...") # Truncate detailed desc
                        
                        await context.bot.send_message(uid, msg, parse_mode='HTML')
                        break # One alert per check to avoid spam
            except Exception as user_err:
                logger.error(f"Error processing severe weather alert for user {user.get('user_id')}: {user_err}")
                    
    except Exception as e:
        logger.error(f"Critical error in severe weather alerts job: {e}")
