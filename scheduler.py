import logging
import datetime
import pytz
from telegram.ext import ContextTypes
from database import (
    get_all_active_users, update_last_notification, get_user_cities, 
    save_weather_history, get_primary_city
)
from weather import get_forecast
from recommendations import format_daily_forecast
from smart_alerts import check_rain_alerts, check_uv_alerts, check_air_quality_alerts, check_severe_weather

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
    """
    try:
        users = await get_all_active_users()
        utc_now = datetime.datetime.now(pytz.utc)
        
        for user in users:
            try:
                user_id = user['user_id']
                # Need to fetch city details from new table
                city_data = await get_primary_city(user_id)
                
                if not city_data:
                    logger.warning(f"User {user_id} has no primary city. Skipping.")
                    continue

                lat = city_data['latitude']
                lon = city_data['longitude']
                city_name = city_data['city_name']
                
                pref_time_str = user['notification_time']
                timezone_str = user['timezone']
                sensitivity = user['temperature_sensitivity']
                last_notif = user['last_notification']
                name = user['user_name'] or "друг"

                # Timezone check
                try:
                    user_tz = pytz.timezone(timezone_str)
                    user_local_time = utc_now.astimezone(user_tz)
                except Exception:
                    user_tz = pytz.timezone('Europe/Moscow')
                    user_local_time = utc_now.astimezone(user_tz)

                if user_local_time.strftime("%H:%M") != pref_time_str:
                    continue

                # Once per day check
                if last_notif:
                    try:
                        last_notif_dt = datetime.datetime.strptime(last_notif, "%Y-%m-%d %H:%M:%S")
                        last_notif_dt = last_notif_dt.replace(tzinfo=pytz.utc)
                        last_notif_local = last_notif_dt.astimezone(user_tz)
                        if last_notif_local.date() == user_local_time.date():
                            continue
                    except ValueError:
                        pass

                logger.info(f"Sending daily notification to user {user_id}...")

                forecast = await get_forecast(lat=lat, lon=lon)
                if not forecast:
                    continue

                content = format_daily_forecast(forecast, sensitivity, city_name, name)
                greeting = get_greeting(name, user_local_time.hour)
                
                message = f"{greeting}\n\n{content}"
                
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
                await update_last_notification(user_id)

            except Exception as u_e:
                logger.error(f"Error processing user {user.get('user_id')}: {u_e}")

    except Exception as e:
        logger.error(f"Error in daily notification job: {e}")

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
    
    # Existing Daily Notifications (every minute check)
    # misfire_grace_time=30 means: if job is late by >30s, skip it
    job_queue.run_repeating(
        send_daily_notifications, 
        interval=60, 
        first=10,
        name="daily_notifications",
        job_kwargs={'misfire_grace_time': 30}
    )
    
    # History Job (End of day) - once per day at 23:55
    job_queue.run_repeating(
        save_daily_history_job, 
        interval=86400, 
        first=80000,
        name="daily_history",
        job_kwargs={'misfire_grace_time': 300}
    )
    
    # Smart Alerts
    # Rain - every hour
    job_queue.run_repeating(
        check_rain_alerts, 
        interval=3600, 
        first=30,
        name="rain_alerts",
        job_kwargs={'misfire_grace_time': 60}
    )
    
    # UV - every 3 hours (optimized from hourly)
    job_queue.run_repeating(
        check_uv_alerts, 
        interval=10800,  # 3 hours instead of 1
        first=40,
        name="uv_alerts",
        job_kwargs={'misfire_grace_time': 120}
    )
    
    # Air Quality - every 6 hours
    job_queue.run_repeating(
        check_air_quality_alerts, 
        interval=21600, 
        first=50,
        name="air_quality_alerts",
        job_kwargs={'misfire_grace_time': 180}
    )
    
    # Severe Weather - every hour
    job_queue.run_repeating(
        check_severe_weather, 
        interval=3600, 
        first=60,
        name="severe_weather_alerts",
        job_kwargs={'misfire_grace_time': 60}
    )
    
    logger.info("✅ Scheduler configured with 6 jobs.")
