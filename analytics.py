"""
Weather analytics and insights generation.
"""
import datetime
from weather import get_current_weather

def generate_comparison_text(today_temp: float, yesterday_temp: float) -> str:
    """Generates a text comparing today's temperature with yesterday's."""
    diff = today_temp - yesterday_temp
    if abs(diff) < 1:
        return "🌡️ Температура как вчера"
    
    direction = "теплее" if diff > 0 else "холоднее"
    emoji = "📈" if diff > 0 else "📉"
    
    return f"📊 {emoji} Сегодня на {abs(diff):.0f}°C {direction} чем вчера"

def generate_weekly_trend_graph(history_data: list) -> str:
    """
    Generates an emoji graph for the last 7 days.
    history_data: list of dicts with 'date' and 'temp_max'/'temp_avg'.
    """
    if not history_data:
        return ""
        
    # Sort by date asc — handle both string and date objects
    def get_date_key(x):
        d = x.get('date')
        if isinstance(d, str):
            return datetime.datetime.strptime(d, "%Y-%m-%d").date()
        elif isinstance(d, datetime.date):
            return d
        elif isinstance(d, datetime.datetime):
            return d.date()
        return datetime.date.min
    
    history_data = sorted(history_data, key=get_date_key)
    
    lines = ["📊 <b>Температура за неделю:</b>"]
    
    # Mapping days
    days_map = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}
    
    # Analyze trend for arrows
    prev_temp = None
    
    for day in history_data:
        date_val = day.get('date')
        if isinstance(date_val, str):
            date_obj = datetime.datetime.strptime(date_val, "%Y-%m-%d")
        elif isinstance(date_val, datetime.datetime):
            date_obj = date_val
        elif isinstance(date_val, datetime.date):
            date_obj = datetime.datetime.combine(date_val, datetime.time.min)
        else:
            continue
            
        day_name = days_map[date_obj.weekday()]
        temp = day.get('temp_max') or day.get('temp_avg') or 0
        
        bar_len = max(0, int(temp / 2)) if temp > 0 else 0
        bar = "━" * bar_len
        
        arrow = ""
        if prev_temp is not None:
            if temp > prev_temp: arrow = " ⬆️"
            elif temp < prev_temp: arrow = " ⬇️"
            
        lines.append(f"{day_name} {bar} {temp:.0f}°C{arrow}")
        prev_temp = temp
        
    return "\n".join(lines)

def calculate_comfort_score(temp, humidity, wind) -> int:
    """Calculates a simple 0-100 comfort score."""
    score = 100
    # Deduct for extremes
    if temp < 10 or temp > 28: score -= 10
    if temp < 0 or temp > 35: score -= 20
    
    if humidity > 80 or humidity < 20: score -= 10
    if wind > 10: score -= 10
    if wind > 20: score -= 20
    
    return max(0, score)

def suggest_activities(weather_data: dict) -> list:
    """
    Suggests activities based on weather.
    weather_data should have 'temp', 'condition_code', 'wind', 'precipitation' (bool)
    """
    temp = weather_data.get('temp', 20)
    code = weather_data.get('condition_code', 1000)
    wind = weather_data.get('wind', 0)
    
    activities = []
    
    is_rain = 200 <= code < 600 or 1000 < code < 1300 # Rough check if strict OWM/WeatherAPI mapping
    # Assuming OWM codes mapped in weather.py
    
    if not is_rain and 15 <= temp <= 25 and wind < 10:
        activities.append("🚶 Прогулка в парке")
        activities.append("🚴 Велопрогулка")
        activities.append("📸 Фотосессия на природе")
    
    if is_rain:
        activities.append("📚 Чтение книги дома")
        activities.append("☕ Поход в кофейню")
        activities.append("🎬 Просмотр кино")
        
    if temp > 25 and not is_rain:
        activities.append("🏖️ Пляж или бассейн")
        activities.append("🍦 Мороженое в парке")
        
    if temp < 0 and not is_rain:
        activities.append("⛸️ Катание на коньках")
        activities.append("🧣 Зимняя прогулка")
        
    return activities

def analyze_best_activity_time(hourly_forecast: list) -> str:
    """
    Analyzes hourly forecast to find best windows.
    Returns formatted string.
    """
    if not hourly_forecast:
        return ""
        
    # Find sequence of "good" hours
    best_hours = []
    
    for item in hourly_forecast:
        # Check condition
        code = item['weather'][0]['id']
        temp = item['main']['temp']
        wind = item['wind']['speed']
        
        # Good: No rain, temp 15-28, wind < 15
        is_good = (code >= 800) and (15 <= temp <= 28) and (wind < 15)
        
        if is_good:
            # Parse time
            dt_txt = item.get('dt_txt', '') # "YYYY-MM-DD HH:MM:SS"
            if not dt_txt: continue
            hour = int(dt_txt.split(' ')[1].split(':')[0])
            best_hours.append(hour)
            
    if not best_hours:
        return ""
        
    # Group into windows
    # (Simplified: find longest streak or just first good window)
    if not best_hours: return ""
    
    start = best_hours[0]
    end = best_hours[0]
    
    # Just take the first block
    # Logic to find ranges: [14, 15, 16] -> 14:00 - 16:00
    # This is a bit complex to implement perfectly in one shot, let's take a simple approach
    # Just "14:00 - 16:00" if we have 14, 15, 16.
    
    # Let's find contiguous blocks
    ranges = []
    current_range = [best_hours[0]]
    
    for h in best_hours[1:]:
        if h == current_range[-1] + 1:
            current_range.append(h)
        else:
            ranges.append(current_range)
            current_range = [h]
    ranges.append(current_range)
    
    # Pick best range (longest or earliest?)
    best_range = max(ranges, key=len)
    
    start_h = best_range[0]
    end_h = best_range[-1] + 1 # +1 to show end of interval usually
    
    return f"✨ <b>Лучшее время для прогулки:</b>\n🌤️ {start_h:02d}:00 - {end_h:02d}:00 (хорошая погода, без осадков)"

def format_uv_recommendation(uv_index: int) -> str:
    level = ""
    rec = ""
    
    if uv_index <= 2:
        level = "Низкий"
        rec = "Защита не требуется"
    elif uv_index <= 5:
        level = "Средний"
        rec = "• Используйте солнцезащитный крем SPF 30+\n• Носите солнечные очки"
    elif uv_index <= 7:
        level = "Высокий"
        rec = "• Обязательно защищайтесь от солнца\n• Избегайте солнца с 11:00 до 16:00"
    elif uv_index <= 10:
        level = "Очень высокий"
        rec = "• Старайтесь не выходить на солнце"
    else:
        level = "Экстремальный"
        rec = "⛔ Не выходите на солнце!"
        
    return f"☀️ <b>УФ-индекс:</b> {uv_index} ({level})\n🧴 <b>Рекомендации:</b>\n{rec}"

def format_aqi_message(aqi_val: int) -> str:
    color = "🟢"
    status = "Отлично"
    rec = "Отлично для прогулок"
    
    if aqi_val <= 50:
        pass
    elif aqi_val <= 100:
        color = "🟡"
        status = "Хорошо"
        rec = "Можно гулять, но чувствительным людям стоит быть внимательнее"
    elif aqi_val <= 150:
        color = "🟠"
        status = "Умеренно"
        rec = "Ограничьте долгие прогулки"
    elif aqi_val <= 200:
        color = "🔴"
        status = "Плохо"
        rec = "Рекомендуем надеть маску или остаться дома"
    else:
        color = "🟣"
        status = "Очень плохо"
        rec = "⛔ Не выходите на улицу без необходимости"
        
    return f"{color} <b>Качество воздуха:</b> {status} (AQI: {aqi_val})\n💡 {rec}"

def get_smart_insight(weather_data: dict) -> str:
    """Returns a fun/smart insight string."""
    # weather_data: temp, condition_code, humidity, wind, is_day...
    
    temp = weather_data.get('temp', 0)
    humid = weather_data.get('humidity', 0)
    wind = weather_data.get('wind', 0)
    code = weather_data.get('condition_code', 800)
    
    # Logic examples
    if 200 <= code < 600 and "sun" in str(code): # Hard to detect sun + rain from code alone without precise current conditions
        pass
    
    if code == 800 and 18 <= temp <= 25 and wind < 5:
        return "🌟 Идеальная погода для пикника!"
        
    if code == 800 and wind < 5 and humid < 50:
        return "👕 Отличный день для сушки белья на улице!"
        
    if code >= 800 and temp > 15 and humid > 80:
        return "💧 Высокая влажность - волосы могут завиваться!"
        
    return ""
