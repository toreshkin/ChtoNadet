import aiohttp
import logging
from config import WEATHERAPI_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://api.weatherapi.com/v1"

def map_condition_code(code: int) -> int:
    """Maps WeatherAPI condition codes to approximate OWM codes."""
    # https://www.weatherapi.com/docs/weather_conditions.json
    
    # 2xx Thunderstorm
    if code in [1087, 1273, 1276, 1279, 1282]:
        return 200
    
    # 3xx Drizzle
    if code in [1063, 1072, 1150, 1153, 1168, 1171, 1180, 1183, 1186, 1189, 1198, 1201, 1240, 1243]:
        return 300
    
    # 5xx Rain (Stronger rain)
    if code in [1192, 1195, 1243, 1246]:
        return 500
        
    # 6xx Snow
    if code in [1066, 1069, 1114, 1117, 1204, 1207, 1210, 1213, 1216, 1219, 1222, 1225, 1237, 1249, 1252, 1255, 1258, 1261, 1264]:
        return 600

    # 7xx Atmosphere (Fog/Mist)
    if code in [1030, 1135, 1147]:
        return 700

    # 8xx Clear/Clouds
    return 800

async def get_coordinates(city_name: str):
    """Gets coordinates for a city name matching the interface expected."""
    async with aiohttp.ClientSession() as session:
        params = {
            "key": WEATHERAPI_KEY,
            "q": city_name,
            "lang": "ru"
        }
        # Using search endpoint for better matching or directly forecast which returns location
        # The user requested using forecast.json mostly, but search.json is standard for this.
        # Let's use search.json specifically for the "get coordinates" step.
        try:
            async with session.get(f"{BASE_URL}/search.json", params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data:
                    return None
                # Return first match
                return data[0]['lat'], data[0]['lon']
        except Exception as e:
            logger.error(f"Error in get_coordinates: {e}")
            return None

async def get_current_weather(lat: float = None, lon: float = None, city: str = None):
    """Fetches current weather and transforms to OWM format."""
    async with aiohttp.ClientSession() as session:
        q_param = f"{lat},{lon}" if lat is not None and lon is not None else city
        if not q_param:
            return None

        params = {
            "key": WEATHERAPI_KEY,
            "q": q_param,
            "lang": "ru",
            "aqi": "no"
        }

        try:
            # Using current.json as it is lighter, but user mentioned forecast.json.
            # However, looking at requirements "API endpoint: https://api.weatherapi.com/v1/forecast.json"
            # I will use forecast.json even for current to strictly adhere, 
            # though current.json is more appropriate. 
            # Actually, reusing logic is good.
            async with session.get(f"{BASE_URL}/forecast.json", params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Error fetching weather: {resp.status}")
                    return None
                data = await resp.json()
                
                # Transform to OWM Current Weather interface
                # Expected: {'main': {'temp': x}, 'weather': [{'description': y, 'id': z}]}
                
                curr = data.get('current', {})
                condition = curr.get('condition', {})
                
                owm_format = {
                    'main': {
                        'temp': curr.get('temp_c'),
                        'feels_like': curr.get('feelslike_c'),
                        'humidity': curr.get('humidity')
                    },
                    'weather': [{
                        'description': condition.get('text'),
                        'id': map_condition_code(condition.get('code', 1000))
                    }],
                    'wind': {
                        'speed': curr.get('wind_kph', 0) / 3.6
                    },
                    'timezone': 0 # Not used critically, simplified
                }
                return owm_format
                
        except Exception as e:
            logger.error(f"Exception in get_current_weather: {e}")
            return None

async def get_forecast(lat: float = None, lon: float = None, city: str = None):
    """Fetches 1-day forecast and transforms to OWM list format for recommendations."""
    async with aiohttp.ClientSession() as session:
        q_param = f"{lat},{lon}" if lat is not None and lon is not None else city
        if not q_param:
            return None

        params = {
            "key": WEATHERAPI_KEY,
            "q": q_param,
            "days": 1,
            "lang": "ru",
            "aqi": "no"
        }

        try:
            async with session.get(f"{BASE_URL}/forecast.json", params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Error fetching forecast: {resp.status}")
                    return None
                data = await resp.json()
                
                forecast_days = data.get('forecast', {}).get('forecastday', [])
                if not forecast_days:
                    return None
                
                # We only requested 1 day.
                hourly_data = forecast_days[0].get('hour', [])
                
                # Transform to OWM List format
                # recommendations.py expects 'list'
                
                transformed_list = []
                for hour in hourly_data:
                    # hour['time'] is "YYYY-MM-DD HH:MM"
                    # OWM uses "YYYY-MM-DD HH:MM:SS"
                    time_str = hour.get('time')
                    if len(time_str) == 16: # 2024-01-28 06:00
                        time_str += ":00"
                    
                    item = {
                        'dt_txt': time_str,
                        'main': {
                            'temp': hour.get('temp_c'),
                            'feels_like': hour.get('feelslike_c'),
                            'humidity': hour.get('humidity')
                        },
                        'weather': [{
                            'description': hour.get('condition', {}).get('text'),
                            'id': map_condition_code(hour.get('condition', {}).get('code', 1000))
                        }],
                        'wind': {
                            'speed': hour.get('wind_kph', 0) / 3.6
                        }
                    }
                    transformed_list.append(item)
                
                return {'list': transformed_list}

        except Exception as e:
            logger.error(f"Exception in get_forecast: {e}")
            return None
            logger.error(f"Exception in get_forecast: {e}")
            return None

async def get_air_quality(city: str) -> dict:
    """Fetches air quality data."""
    async with aiohttp.ClientSession() as session:
        params = {
            "key": WEATHERAPI_KEY,
            "q": city,
            "aqi": "yes"
        }
        try:
            async with session.get(f"{BASE_URL}/current.json", params=params) as resp:
                if resp.status != 200: return None
                data = await resp.json()
                aqi_data = data.get('current', {}).get('air_quality', {})
                # WeatherAPI returns 'us-epa-index' or 'gb-defra-index'
                # But for standard AQI (0-500), mostly people use 'pm2_5' or 'pm10' to calculate, 
                # or rely on 'us-epa-index' (1-6 scale).
                # The user asked for 0-50 colors (Standard AQI). 
                # WeatherAPI does NOT return standard 0-500 AQI directly in the free tier usually?
                # Actually it returns 'us-epa-index' (1-6) and 'gb-defra-index'.
                # However, it DOES return raw pollutant numbers.
                # Use US-EPA index mapping or approximation?
                # Wait, prompt says: "0-50: Good". This is standard AQI.
                # We might need to calculate it or check if WeatherAPI provides it.
                # Actually, WeatherAPI generally provides 'us-epa-index'.
                # 1 = Good, 2 = Moderate, 3 = Unhealthy for sensitive, 4 = Unhealthy, 5 = Very Unhealthy, 6 = Hazardous.
                # The prompt asks for 0-50, 51-100...
                # Let's try to map EPA index to a range or just return the raw 'us-epa-index' and handle display logic?
                # OR use the 'pm25' value to estimate AQI using a helper?
                # Let's return raw dictionary + calculated standard AQI estimate.
                
                pm2_5 = aqi_data.get('pm2_5', 0)
                # Quick approx calculation of US AQI from PM2.5
                # Simple linear interpolation for ranges?
                # Real algorithm is complex. Let's use a simplified version because strict calculation is heavy.
                # For MVP, maybe return data as is, and let analytics.py format it?
                # User asked for `get_air_quality(city: str) -> dict`. 
                # I will return the full 'air_quality' object + an estimated 'aqi_val' key.
                
                aqi_val = 0
                if pm2_5 <= 12.0:
                    aqi_val = ((50 - 0) / (12.0 - 0)) * (pm2_5 - 0) + 0
                elif pm2_5 <= 35.4:
                    aqi_val = ((100 - 51) / (35.4 - 12.1)) * (pm2_5 - 12.1) + 51
                elif pm2_5 <= 55.4:
                    aqi_val = ((150 - 101) / (55.4 - 35.5)) * (pm2_5 - 35.5) + 101
                elif pm2_5 <= 150.4:
                    aqi_val = ((200 - 151) / (150.4 - 55.5)) * (pm2_5 - 55.5) + 151
                else:
                    aqi_val = 201 # Very bad
                
                aqi_data['aqi_val'] = int(aqi_val)
                return aqi_data
        except Exception:
            return None

async def get_uv_index(city: str) -> int:
    """Fetches UV index."""
    async with aiohttp.ClientSession() as session:
        params = {"key": WEATHERAPI_KEY, "q": city}
        try:
            async with session.get(f"{BASE_URL}/current.json", params=params) as resp:
                if resp.status != 200: return 0
                data = await resp.json()
                return int(data.get('current', {}).get('uv', 0))
        except Exception:
            return 0

async def check_rain_in_next_hours(city: str, hours: int = 2) -> dict:
    """
    Checks for rain in the upcoming hours.
    Returns dict with {will_rain: bool, start_time: str, intensity: str}
    """
    # Use forecast.json
    async with aiohttp.ClientSession() as session:
        params = {"key": WEATHERAPI_KEY, "q": city, "days": 1, "aqi": "no", "alerts": "no"}
        try:
            async with session.get(f"{BASE_URL}/forecast.json", params=params) as resp:
                if resp.status != 200: return None
                data = await resp.json()
                
                forecast_day = data.get('forecast', {}).get('forecastday', [])
                if not forecast_day: return None
                
                hourly = forecast_day[0].get('hour', [])
                
                import datetime
                import pytz
                
                # We need to find "current hour" in the list.
                # WeatherAPI returns hours in local time of the location usually or proper epoch.
                # Let's use epoch 'time_epoch' for reliable comparison.
                now_epoch = datetime.datetime.now().timestamp()
                
                upcoming_rain = []
                
                for h in hourly:
                    h_epoch = h.get('time_epoch')
                    if h_epoch > now_epoch and h_epoch <= now_epoch + (hours * 3600):
                        # check rain
                        if h.get('will_it_rain', 0) == 1 or h.get('chance_of_rain', 0) > 60:
                             upcoming_rain.append(h)
                             
                if upcoming_rain:
                    first = upcoming_rain[0]
                    return {
                        'will_rain': True,
                        'start_time': first.get('time').split(' ')[1], # "HH:MM"
                        'intensity': first.get('condition', {}).get('text'),
                        'chance': first.get('chance_of_rain')
                    }
                return {'will_rain': False}

        except Exception:
            return None

async def get_severe_weather_alerts(city: str) -> list:
    """Fetches weather alerts."""
    async with aiohttp.ClientSession() as session:
        params = {"key": WEATHERAPI_KEY, "q": city, "days": 1, "alerts": "yes"}
        try:
            async with session.get(f"{BASE_URL}/forecast.json", params=params) as resp:
                if resp.status != 200: return []
                data = await resp.json()
                return data.get('alerts', {}).get('alert', [])
        except Exception:
            return []
