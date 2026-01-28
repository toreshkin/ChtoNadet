def get_clothing_advice(temperature: float, condition_id: int, wind_speed: float, sensitivity: str = "normal", name: str = "друг") -> str:
    """
    Generates clothing recommendations based on weather and user sensitivity.
    """
    
    # Adjust temperature based on sensitivity
    effective_temp = temperature
    if sensitivity == "cold_sensitive":
        effective_temp -= 5
    elif sensitivity == "heat_sensitive":
        effective_temp += 5
    
    advice = []
    
    # Gradient of comments based on Temp
    if effective_temp < -15:
        advice.append("🥶 <b>Очень холодно!</b> Нужен толстый пуховик, теплый свитер, шапка, шарф и варежки.")
    elif -15 <= effective_temp < -5:
        advice.append("❄️ <b>Морозно.</b> Надевайте зимнюю куртку или пальто, свитер, шапку и перчатки.")
    elif -5 <= effective_temp < 5:
        advice.append("🧥 <b>Прохладно.</b> Подойдет теплая куртка и легкий свитер.")
    elif 5 <= effective_temp < 15:
        advice.append("🌤 <b>Свежо.</b> Надевайте демисезонную куртку, худи или плащ.")
    elif 15 <= effective_temp < 20:
        advice.append("😌 <b>Комфортно.</b> Легкая куртка, пиджак или кофта.")
    elif 20 <= effective_temp < 25:
        advice.append("😎 <b>Тепло.</b> Футболка, джинсы или легкое платье.")
    else: # >= 25
        advice.append("🥵 <b>Жарко!</b> Шорты, майка, сандалии. Одевайтесь максимально легко.")

    # Precipitation handling
    if 200 <= condition_id < 600:
        advice.append("\n☔️ Ожидается дождь/гроза. <b>Не забудьте зонт</b> и непромокаемую обувь!")
    elif 600 <= condition_id < 700:
        advice.append("\n🌨 Возможен снег. Обувь должна быть теплой и не скользкой.")
    
    # Wind handling
    if wind_speed > 7.0: # m/s
        advice.append("\n💨 <b>Сильный ветер.</b> Лучше надеть непродуваемую куртку или ветровку.")

    return f"{name}, советую: " + " ".join(advice)

def format_daily_forecast(forecast_data: dict, sensitivity: str, city_name: str, name: str) -> str:
    """
    Formats the daily forecast message.
    """
    list_data = forecast_data.get('list', [])
    if not list_data:
        return "❌ Не удалось получить прогноз."

    # General info from the first item (closest to now)
    current = list_data[0]
    curr_temp = current['main']['temp']
    curr_feels = current['main']['feels_like']
    curr_wind = current['wind']['speed'] * 3.6 # m/s to km/h for display
    curr_humid = current['main']['humidity']
    
    # Emoji selection
    condition_id = current['weather'][0]['id']
    weather_emoji = get_weather_emoji(condition_id)

    header = (
        f"{weather_emoji} <b>Погода в городе: {city_name}</b>\n\n"
        f"🌡️ <b>Сейчас:</b> {curr_temp:+.0f}°C (ощущается {curr_feels:+.0f}°C)\n"
        f"💨 <b>Ветер:</b> {curr_wind:.1f} км/ч\n"
        f"💧 <b>Влажность:</b> {curr_humid}%\n"
    )

    # Forecast periods
    periods_text = "\n📅 <b>Прогноз на день:</b>\n"
    target_times = {
        "09:00:00": "🌅 Утро (09:00)",
        "15:00:00": "☀️ День (15:00)",
        "21:00:00": "🌇 Вечер (21:00)"
    }
    
    found_periods = 0
    general_clothing_temp = curr_temp # Default to current
    general_id = condition_id
    general_wind = current['wind']['speed']

    for item in list_data:
        dt_txt = item.get('dt_txt', '') # "YYYY-MM-DD HH:MM:SS"
        time_part = dt_txt.split(' ')[1]
        
        if time_part in target_times:
            period_label = target_times[time_part]
            temp = item['main']['temp']
            p_emoji = get_weather_emoji(item['weather'][0]['id'])
            
            periods_text += f"{p_emoji} {period_label}: {temp:+.0f}°C\n"
            
            # Use day temperature for main recommendation if available
            if time_part == "15:00:00":
                general_clothing_temp = temp
                general_id = item['weather'][0]['id']
                general_wind = item['wind']['speed']
            
            found_periods += 1
            if found_periods >= 3:
                break
    
    if found_periods == 0:
        periods_text += "Данных на сегодня больше нет."

    # Clothing advice
    clothing = get_clothing_advice(general_clothing_temp, general_id, general_wind, sensitivity, name)
    
    return f"{header}{periods_text}\n👔 <b>Рекомендации:</b>\n{clothing}"

def get_weather_emoji(code):
    """Maps OWM condition ID to emoji."""
    if 200 <= code < 300: return "⛈️"
    if 300 <= code < 500: return "🌦️"
    if 500 <= code < 600: return "🌧️"
    if 600 <= code < 700: return "❄️"
    if 700 <= code < 800: return "🌫️"
    if code == 800: return "☀️"
    if code == 801: return "🌤️"
    if code == 802: return "⛅"
    if code >= 803: return "☁️"
    return "🌡️"

def sensitivity_to_text(s: str) -> str:
    if s == 'cold_sensitive': return '❄️ Мерзляк'
    if s == 'heat_sensitive': return '🔥 Жаркий'
    return '😊 Нормально'
