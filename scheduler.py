import logging
import datetime
import pytz
from telegram.ext import ContextTypes
from database import (
    get_all_active_users, update_last_notification, 
    save_weather_history, get_primary_city
)
from weather import get_forecast, get_uv_index, get_air_quality
from recommendations import format_daily_forecast

logger = logging.getLogger(__name__)

def get_greeting(name, hour):
    if 6 <= hour < 11:
        return f"Доброе утро, {name}! ☀️"
    elif 11 <= hour < 17:
        return f"Добрый день, {name}! 😊"
    elif 17 <= hour < 23:
        return f"Добрый вечер, {name}! 🌆"
    else:
        return f"Доброй ночи, {name}! 🌙"

async def send_daily_notifications(context: ContextTypes.DEFAULT_TYPE):
    """
    Background task to check and send daily notifications.
    Runs every 60 seconds, uses a 5-minute window for time matching.
    """
    try:
        users = await get_all_active_users()
        utc_now = datetime.datetime.now(pytz.utc)
        
        logger.debug(f"📋 Checking notifications for {len(users)} active users at UTC {utc_now.strftime('%H:%M:%S')}")
        
        for user in users:
            try:
                user_id = user['user_id']
                
                # Check if user has notifications enabled
                if not user.get('is_active', True):
                    continue
                
                # Need to fetch city details from new table
                city_data = await get_primary_city(user_id)
                
                if not city_data:
                    logger.debug(f"⏭ User {user_id}: no primary city, skipping")
                    continue

                lat = city_data['latitude']
                lon = city_data['longitude']
                city_name = city_data['city_name']
                
                pref_time_str = user.get('notification_time', '07:00')
                timezone_str = user.get('timezone', 'Europe/Moscow')
                sensitivity = user.get('temperature_sensitivity', 'normal')
                last_notif = user.get('last_notification')
                name = user.get('user_name') or "друг"

                # Timezone check
                try:
                    user_tz = pytz.timezone(timezone_str)
                    user_local_time = utc_now.astimezone(user_tz)
                except Exception:
                    user_tz = pytz.timezone('Europe/Moscow')
                    user_local_time = utc_now.astimezone(user_tz)

                # Parse preferred notification time
                try:
                    pref_hour, pref_minute = map(int, pref_time_str.split(':'))
                except (ValueError, AttributeError):
                    pref_hour, pref_minute = 7, 0
                
                # Use a 5-minute window for matching to avoid missing notifications
                # This handles scheduler delays, server load, and clock drift
                current_total_minutes = user_local_time.hour * 60 + user_local_time.minute
                pref_total_minutes = pref_hour * 60 + pref_minute
                
                time_diff = abs(current_total_minutes - pref_total_minutes)
                # Also handle midnight wraparound (e.g., pref=23:59, current=00:01)
                time_diff = min(time_diff, 1440 - time_diff)
                
                if time_diff > 2:
                    continue

                # Once per day check — handle both datetime objects and strings
                if last_notif:
                    try:
                        if isinstance(last_notif, datetime.datetime):
                            last_notif_dt = last_notif
                            if last_notif_dt.tzinfo is None:
                                last_notif_dt = last_notif_dt.replace(tzinfo=pytz.utc)
                        elif isinstance(last_notif, str):
                            # Try multiple date formats
                            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"]:
                                try:
                                    last_notif_dt = datetime.datetime.strptime(last_notif, fmt)
                                    last_notif_dt = last_notif_dt.replace(tzinfo=pytz.utc)
                                    break
                                except ValueError:
                                    continue
                            else:
                                last_notif_dt = None
                                logger.warning(f"Could not parse last_notification string for user {user_id}: {last_notif}")
                        else:
                            last_notif_dt = None
                        
                        if last_notif_dt:
                            last_notif_local = last_notif_dt.astimezone(user_tz)
                            if last_notif_local.date() == user_local_time.date():
                                logger.debug(f"⏭ User {user_id}: already notified today")
                                continue  # Already notified today
                    except Exception as parse_err:
                        logger.warning(f"Could not parse last_notification for user {user_id}: {parse_err}")

                logger.info(f"📨 Sending daily notification to user {user_id} (time: {pref_time_str}, tz: {timezone_str}, local: {user_local_time.strftime('%H:%M')})")

                forecast = await get_forecast(lat=lat, lon=lon)
                if not forecast:
                    logger.warning(f"No forecast data for user {user_id}, city {city_name}")
                    continue

                # Fetch UV and AQI for morning notification
                uv = None
                aqi = None
                try:
                    uv = await get_uv_index(city_name)
                except Exception as uv_err:
                    logger.warning(f"Failed to get UV for {city_name}: {uv_err}")
                try:
                    aqi = await get_air_quality(city_name)
                except Exception as aqi_err:
                    logger.warning(f"Failed to get AQI for {city_name}: {aqi_err}")

                try:
                    content = format_daily_forecast(forecast, sensitivity, city_name, name, uv_index=uv, aqi_data=aqi)
                except Exception as fmt_err:
                    logger.error(f"Error formatting forecast for user {user_id}: {fmt_err}", exc_info=True)
                    content = "❌ Не удалось сформировать прогноз."
                    
                greeting = get_greeting(name, user_local_time.hour)
                
                message = f"{greeting}\n\n{content}"
                
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
                await update_last_notification(user_id)
                logger.info(f"✅ Daily notification sent to user {user_id}")

            except Exception as u_e:
                logger.error(f"Error processing user {user.get('user_id')}: {u_e}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in daily notification job: {e}", exc_info=True)

async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """
    Runs every 3 hours. Checks for dramatic weather changes in the next 6-12 hours.
    Simple logic: drop > 10 degrees.
    """
    try:
        users = await get_all_active_users()
        for user in users:
            if not user.get('alerts_enabled'):
                continue
                
            user_id = user['user_id']
            city_data = await get_primary_city(user_id)
            if not city_data: continue
            
            lat, lon = city_data['latitude'], city_data['longitude']
            name = user['user_name']
            
            forecast = await get_forecast(lat=lat, lon=lon)
            if not forecast or 'list' not in forecast: continue
            
            # forecast list is 3-hourly or hourly depending on API, but mapped to list in weather.py
            # weather.py maps to 'list'. We iterated 1 day.
            # Let's find max diff.
            
            temps = [item['main']['temp'] for item in forecast['list']]
            if not temps: continue
            
            max_t = max(temps)
            min_t = min(temps)
            
            # Simple alert: if drop is massive
            if (max_t - min_t) > 10:
                pass 
                
    except Exception as e:
        logger.error(f"Error in alerts job: {e}")

async def save_daily_history_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Runs at 23:55 to save today's stats.
    """
    try:
        users = await get_all_active_users()
        today_str = datetime.date.today().isoformat()
        
        for user in users:
            city_data = await get_primary_city(user['user_id'])
            if not city_data: continue
            
            lat, lon = city_data['latitude'], city_data['longitude']
            city_name = city_data['city_name']
            
            forecast = await get_forecast(lat=lat, lon=lon)
            if not forecast: continue
            
            # Extract stat from list (which assumes 1 day forecast)
            list_data = forecast['list']
            temps = [x['main']['temp'] for x in list_data]
            
            if not temps: continue
            
            avg_temp = sum(temps) / len(temps)
            min_temp = min(temps)
            max_temp = max(temps)
            
            data = {
                'temp_avg': avg_temp,
                'temp_min': min_temp,
                'temp_max': max_temp,
                'condition': list_data[0]['weather'][0]['description'], # Roughly
                'precipitation': 0, # not parsed currently
                'wind_speed': list_data[0]['wind']['speed']
            }
            
            await save_weather_history(user['user_id'], city_name, today_str, data)
            
    except Exception as e:
        logger.error(f"Error in history job: {e}")

def setup_scheduler(application):
    """
    Configures all scheduled jobs.
    """
    job_queue = application.job_queue
    
    # Daily Notifications (check every 60 seconds)
    # misfire_grace_time=120 means: if job is late by >120s, skip it
    # This is more lenient to handle server load/restarts
    job_queue.run_repeating(
        send_daily_notifications, 
        interval=60, 
        first=10,
        name="daily_notifications",
        job_kwargs={'misfire_grace_time': 120}
    )
    
    # History Job (End of day) - once per day at 20:55 UTC (~23:55 Moscow)
    import datetime as dt
    job_queue.run_daily(
        save_daily_history_job, 
        time=dt.time(hour=20, minute=55, tzinfo=pytz.utc),
        name="daily_history",
        job_kwargs={'misfire_grace_time': 600}
    )
    
    # Smart Alerts - DISABLED due to user feedback (spam)
    # They were firing too frequently without sufficient state tracking.
    
    # Rain - every hour (DISABLED)
    # job_queue.run_repeating(
    #     check_rain_alerts, 
    #     interval=3600, 
    #     first=30,
    #     name="rain_alerts",
    #     job_kwargs={'misfire_grace_time': 60}
    # )
    
    # UV - every 3 hours (optimized from hourly) (DISABLED)
    # job_queue.run_repeating(
    #     check_uv_alerts, 
    #     interval=10800,  # 3 hours instead of 1
    #     first=40,
    #     name="uv_alerts",
    #     job_kwargs={'misfire_grace_time': 120}
    # )
    
    # Air Quality - every 6 hours (DISABLED)
    # job_queue.run_repeating(
    #     check_air_quality_alerts, 
    #     interval=21600, 
    #     first=50,
    #     name="air_quality_alerts",
    #     job_kwargs={'misfire_grace_time': 180}
    # )
    
    # Severe Weather - every hour (DISABLED)
    # job_queue.run_repeating(
    #     check_severe_weather, 
    #     interval=3600, 
    #     first=60,
    #     name="severe_weather_alerts",
    #     job_kwargs={'misfire_grace_time': 60}
    # )
    
    logger.info("✅ Scheduler configured: daily notifications every 60s (grace=120s), history daily at 20:55 UTC")
