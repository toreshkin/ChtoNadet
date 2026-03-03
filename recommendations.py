def get_clothing_advice(temperature: float, condition_id: int, wind_speed: float, sensitivity: str = "normal", name: str = "друг") -> str:
    """
    Generates detailed clothing recommendations (headwear, outerwear, footwear).
    """
    
    # Adjust temperature based on sensitivity
    effective_temp = temperature
    if sensitivity == "cold_sensitive":
        effective_temp -= 5
    elif sensitivity == "heat_sensitive":
        effective_temp += 5
    
    # Categories
    headwear = ""
    outerwear = ""
    footwear = ""
    additional = []
    tips = []  # Дополнительные советы
    
    # Base logic based on Temp
    if effective_temp < -15:
        headwear = "Тёплая зимняя шапка и шарф 🧣"
        outerwear = "Толстый пуховик, тёплый свитер и термобельё 🧥"
        footwear = "Зимние ботинки с мехом 👢"
        additional.append("варежки или тёплые перчатки 🧤")
        tips.append("Старайтесь не находиться на улице долго")
        tips.append("Закрывайте лицо шарфом при сильном ветре")
    elif -15 <= effective_temp < -5:
        headwear = "Зимняя шапка 🧢"
        outerwear = "Зимняя куртка или пальто, свитер 🧥"
        footwear = "Зимние ботинки 🥾"
        additional.append("перчатки 🧤")
        tips.append("Одевайтесь слоями для лучшей теплоизоляции")
    elif -5 <= effective_temp < 5:
        headwear = "Лёгкая шапка (по желанию) 🧢"
        outerwear = "Тёплая куртка и лёгкий свитер 🧥"
        footwear = "Ботинки или утеплённые кроссовки 👟"
        tips.append("Возьмите шарф на случай ветра")
    elif 5 <= effective_temp < 15:
        outerwear = "Демисезонная куртка, худи или плащ 🧥"
        footwear = "Кроссовки или туфли 👟"
        tips.append("Идеальная погода для прогулок")
    elif 15 <= effective_temp < 20:
        outerwear = "Лёгкая куртка, ветровка или плотная кофта 🧥"
        footwear = "Кроссовки или лоферы 👟"
        tips.append("Комфортная температура для активностей")
    elif 20 <= effective_temp < 25:
        outerwear = "Футболка с длинным рукавом или рубашка 👕"
        footwear = "Лёгкие кроссовки или кеды 👟"
        tips.append("Отличная погода для спорта на свежем воздухе")
    else: # >= 25
        outerwear = "Футболка, шорты или лёгкое платье 👕"
        footwear = "Сандалии или максимально лёгкие кеды 👡"
        tips.append("Пейте больше воды")
        tips.append("Избегайте прямых солнечных лучей в полдень")

    # Precipitation handling
    if 200 <= condition_id < 600:
        additional.append("<b>возьмите зонт</b> ☔️")
        footwear = "Непромокаемая обувь ☔️"
        tips.append("Ожидаются осадки - будьте готовы")
    elif 600 <= condition_id < 700:
        headwear = "Тёплая шапка ❄️"
        additional.append("перчатки 🧤")
        footwear = "Тёплая и не скользкая обувь ❄️"
        tips.append("Осторожно, возможен гололёд")
    
    # Wind handling
    if wind_speed > 7.0: # m/s
        outerwear = "Непродуваемая ветровка или плотная куртка 💨"
        if not headwear and effective_temp < 15:
            headwear = "Лёгкая шапка или капюшон 🧢"
        tips.append("Сильный ветер - одевайтесь теплее")

    advice_parts = []
    if headwear:
        advice_parts.append(f"  🧢 <b>Голова:</b> {headwear}")
    if outerwear:
        advice_parts.append(f"  🧥 <b>Верх:</b> {outerwear}")
    if footwear:
        advice_parts.append(f"  👟 <b>Обувь:</b> {footwear}")
    if additional:
        advice_parts.append(f"  ➕ <b>Дополнительно:</b> {', '.join(additional)}")
    
    result = "\n".join(advice_parts)
    
    # Add tips if any
    if tips:
        tips_text = "\n".join(f"  💡 {tip}" for tip in tips[:2])  # Максимум 2 совета
        result += f"\n\n<b>💬 Советы</b>\n{tips_text}"
    
    return result

def format_daily_forecast(forecast_data: dict, sensitivity: str, city_name: str, name: str, uv_index: int = None, aqi_data: dict = None) -> str:
    """
    Formats the daily forecast message.
    """
    from analytics import format_uv_recommendation, format_aqi_message

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

    if uv_index is not None:
        header += f"☀️ <b>УФ-индекс:</b> {uv_index}\n"
    
    if aqi_data and 'aqi_val' in aqi_data:
        aqi_val = aqi_data['aqi_val']
        header += f"🌫️ <b>AQI:</b> {aqi_val}\n"

    # Forecast periods
    periods_text = "\n📅 <b>Прогноз на день</b>\n"
    target_times = {
        "09:00:00": "🌅 Утро",
        "15:00:00": "☀️ День",
        "21:00:00": "🌇 Вечер"
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
            
            periods_text += f"├ {period_label}: <b>{temp:+.0f}°C</b> {p_emoji}\n"
            
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
    
    # UV and AQI details (optional, but requested for morning notification)
    details = ""
    if uv_index is not None or aqi_data:
        details = "\n📊 <b>Дополнительно:</b>\n"
        if uv_index is not None:
             uv_full = format_uv_recommendation(uv_index)
             uv_parts = uv_full.split("\n", 1)
             uv_text = uv_parts[1] if len(uv_parts) > 1 else uv_full
             details += uv_text + "\n"
        if aqi_data:
             aqi_text = format_aqi_message(aqi_data.get('aqi_val', 0))
             details += aqi_text + "\n"

    return f"{header}{periods_text}\n{details}\n👔 <b>Рекомендации:</b>\n{clothing}"

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
