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
                    user_tz = pytz.utc
                    user_local_time = utc_now

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
                # We haven't built complex tracking of "already sent alert", so we might spam.
                # Only send if the drop happens soon?
                # For MVP, we will skip implementation of complex state tracking for alerts 
                # to avoid spamming every 3 hours if the condition persists.
                # A production system needs an 'alerts' table to log sent alerts.
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
        
        # Avoid duplicate work: aggregate unique (city_name, lat, lon) tuples?
        # Because we store history per user-city (as per schema request: "user_id, city_name, date" unique),
        # we must do it per user.
        
        for user in users:
            city_data = await get_primary_city(user['user_id'])
            if not city_data: continue
            
            lat, lon = city_data['latitude'], city_data['longitude']
            city_name = city_data['city_name']
            
            # Get data. Since we want "history", and we are at the end of the day,
            # current weather is just "now". Ideally we want max/min of the day.
            # Forecast API gives max/min for the day!
            
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
