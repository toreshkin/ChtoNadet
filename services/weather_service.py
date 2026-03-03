import logging
import datetime
from database import get_user, save_weather_snapshot, get_weather_comparison
from weather import get_forecast, get_current_weather, get_uv_index, get_air_quality
from analytics import generate_comparison_text, get_smart_insight, suggest_activities
from recommendations import get_weather_emoji, get_clothing_advice
from streak import get_streak_info, get_streak_message

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
        comp_text = f"<blockquote>{comp_text}</blockquote>"
    
    # Save NEW snapshot
    try:
        await save_weather_snapshot(user_id, city_name, current['main']['temp'], current['weather'][0]['description'])
    except Exception as snap_err:
        logger.warning(f"Failed to save weather snapshot: {snap_err}")

    # 3. Format Strings
    temp = current['main']['temp']
    feels = current['main']['feels_like']
    cond = current['weather'][0]['description']
    cond = cond.capitalize()
    emoji_icon = get_weather_emoji(current['weather'][0]['id'])
    
    # Details
    wind = current['wind']['speed'] * 3.6 # km/h
    humid = current['main']['humidity']
    pressure = current['main'].get('pressure', 0)
    aqi_val = aqi_data.get('aqi_val', 'N/A') if aqi_data else 'N/A'
    
    # Recommendations
    sens = user.get('temperature_sensitivity', 'normal')
    name = user.get('user_name', 'друг')
    clothing = get_clothing_advice(temp, current['weather'][0]['id'], wind/3.6, sens, name)
    
    # Activity suggestions
    activities = suggest_activities({
        'temp': temp,
        'condition_code': current['weather'][0]['id'],
        'wind': wind/3.6,
        'precipitation': 200 <= current['weather'][0]['id'] < 700
    })
    
    # Insight
    smart_text = get_smart_insight({'temp': temp, 'humidity': humid, 'wind': wind/3.6, 'condition_code': current['weather'][0]['id']})
    
    # 4. Build Forecast Periods Text
    periods_text = "\n\n📅 <b>Прогноз на день</b>\n"
    target_times = {
        "09:00:00": "🌅 Утро",
        "15:00:00": "☀️ День",
        "21:00:00": "🌇 Вечер"
    }
    found_periods = 0
    if forecast and 'list' in forecast:
        for item in forecast['list']:
            time_part = item.get('dt_txt', '').split(' ')[1]
            if time_part in target_times:
                p_label = target_times[time_part]
                p_temp = item['main']['temp']
                p_emoji = get_weather_emoji(item['weather'][0]['id'])
                periods_text += f"├ {p_label}: <b>{p_temp:+.0f}°C</b> {p_emoji}\n"
                found_periods += 1
    
    if found_periods == 0:
        periods_text = ""
    else:
        # Clean up last line of periods if needed, or just keep it
        pass

    # Build beautiful message
    text = f"""<b>{emoji_icon} Погода в городе: {city_name}</b>

<b>🌡 Температура</b>
├ Сейчас: <b>{temp:+.1f}°C</b>
└ Ощущается: <b>{feels:+.1f}°C</b>
{periods_text}

<b>☁️ Условия:</b> {cond}
{comp_text}

<b>📊 Детали</b>
├ 💨 Ветер: {wind:.1f} км/ч
├ 💧 Влажность: {humid}%
├ 🌡 Давление: {pressure} мбар
├ ☀️ УФ-индекс: {uv if uv is not None else 'N/A'}
└ 🌫️ AQI: {aqi_val}"""

    if smart_text:
        text += f"\n\n💡 <i>{smart_text}</i>"
    
    text += f"\n\n<b>👔 Рекомендации по одежде</b>\n{clothing}"
    
    if activities:
        activities_text = "\n".join(f"  • {act}" for act in activities[:3])
        text += f"\n\n<b>🎯 Чем заняться</b>\n{activities_text}"
    
    return text
