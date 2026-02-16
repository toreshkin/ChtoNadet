import logging
import datetime
from database import get_user, save_weather_snapshot, get_weather_comparison
from weather import get_forecast, get_current_weather, get_uv_index, get_air_quality
from analytics import generate_comparison_text, get_smart_insight
from recommendations import get_weather_emoji, get_clothing_advice

logger = logging.getLogger(__name__)

async def generate_weather_message_content(user_id, city_data):
    if not city_data: return "У вас нет добавленных городов."
    
    lat, lon = city_data['latitude'], city_data['longitude']
    city_name = city_data['city_name']
    
    # 1. Fetch Data
    forecast = await get_forecast(lat=lat, lon=lon)
    current = await get_current_weather(lat=lat, lon=lon)
    uv = await get_uv_index(city_name)
    aqi_data = await get_air_quality(city_name)
    user = await get_user(user_id)
    
    if not current or not forecast: return "Не удалось получить данные о погоде."

    # 2. Comparison
    comp_text = ""
    comp_data = await get_weather_comparison(user_id, city_name)
    if comp_data:
        comp_text = generate_comparison_text(current['main']['temp'], comp_data['temp'])
        comp_text = f"<i>{comp_text}</i>"
    
    # Save NEW snapshot
    try:
        await save_weather_snapshot(user_id, city_name, current['main']['temp'], current['weather'][0]['description'])
    except: pass

    # 3. Format Strings
    temp = current['main']['temp']
    feels = current['main']['feels_like']
    cond = current['weather'][0]['description']
    cond = cond.capitalize()
    emoji_icon = get_weather_emoji(current['weather'][0]['id'])
    
    # Details
    wind = current['wind']['speed'] * 3.6 # km/h
    humid = current['main']['humidity']
    aqi_val = aqi_data.get('aqi_val', 'N/A') if aqi_data else 'N/A'
    
    # Recommendations
    sens = user.get('temperature_sensitivity', 'normal')
    name = user.get('user_name', 'друг')
    clothing = get_clothing_advice(temp, current['weather'][0]['id'], wind/3.6, sens, name)
    rec_text = f"<b>👔 Рекомендации:</b>\n{clothing}"
    
    # Insight
    smart_text = get_smart_insight({'temp': temp, 'humidity': humid, 'wind': wind/3.6, 'condition_code': current['weather'][0]['id']})
    
    text = (
        f"{emoji_icon} <b>Погода в городе: {city_name}</b>\n\n"
        f"🌡️ <b>Температура:</b> {temp:+.1f}°C (ощущается как {feels:+.1f}°C)\n"
        f"☁️ <b>Условия:</b> {cond}\n"
        f"{comp_text}\n\n"
        f"💨 <b>Ветер:</b> {wind:.1f} км/ч\n"
        f"💧 <b>Влажность:</b> {humid}%\n"
        f"☀️ <b>УФ-индекс:</b> {uv if uv is not None else 'N/A'}\n"
        f"🌫️ <b>AQI:</b> {aqi_val}\n\n"
        f"💡 <i>{smart_text}</i>\n\n"
        f"{rec_text}"
    )
    return text
