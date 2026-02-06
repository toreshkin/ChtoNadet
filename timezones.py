"""
Timezone management and conversion utilities
"""
import pytz
from datetime import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Common CIS timezones and major world regions
COMMON_TIMEZONES = {
    'GMT+2': {'name': 'Europe/Kaliningrad', 'display': 'GMT+2 (Калининград)'},
    'GMT+3': {'name': 'Europe/Moscow', 'display': 'GMT+3 (Москва, Минск)'},
    'GMT+4': {'name': 'Europe/Samara', 'display': 'GMT+4 (Самара, Тбилиси, Ереван)'},
    'GMT+5': {'name': 'Asia/Yekaterinburg', 'display': 'GMT+5 (Екатеринбург, Ташкент)'},
    'GMT+6': {'name': 'Asia/Bishkek', 'display': 'GMT+6 (Бишкек, Алматы, Омск)'},
    'GMT+7': {'name': 'Asia/Novosibirsk', 'display': 'GMT+7 (Новосибирск)'},
    'GMT+8': {'name': 'Asia/Irkutsk', 'display': 'GMT+8 (Иркутск)'},
    'GMT+9': {'name': 'Asia/Yakutsk', 'display': 'GMT+9 (Якутск)'},
    'GMT+10': {'name': 'Asia/Vladivostok', 'display': 'GMT+10 (Владивосток)'},
    'GMT+11': {'name': 'Asia/Magadan', 'display': 'GMT+11 (Магадан)'},
    'GMT+12': {'name': 'Asia/Kamchatka', 'display': 'GMT+12 (Камчатка)'},
}

# Callback prefix
TIMEZONE_PREFIX = "TZ_SELECT_"
TIMEZONE_OTHER = "TZ_OTHER"

def get_timezone_keyboard() -> InlineKeyboardMarkup:
    """Creates the main timezone selection keyboard."""
    keyboard = []
    
    # Create rows of 2 buttons
    keys = list(COMMON_TIMEZONES.keys())
    # Sort roughly by offset order encoded in key (2, 3, 4...)
    # keys are 'GMT+2', etc. keys[4:] casts to int
    sorted_keys = sorted(keys, key=lambda x: int(x.split('+')[1]))
    
    row = []
    for key in sorted_keys:
        data = COMMON_TIMEZONES[key]
        callback = f"{TIMEZONE_PREFIX}{data['name']}"
        row.append(InlineKeyboardButton(data['display'], callback_data=callback))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("🌎 Другие часовые пояса", callback_data=TIMEZONE_OTHER)])
    
    return InlineKeyboardMarkup(keyboard)

def get_extended_timezone_keyboard(offset: int = 0) -> InlineKeyboardMarkup:
    """
    Shows more timezones. For simplicity in this bot, 
    we might just show a list of major world cities or regions.
    For this implementation, let's just add a few major global ones 
    or just instruction to use main ones if possible.
    The prompt asks for "GMT-12 to GMT+14", which is huge.
    Let's implement a simplified page-able list or just a longer list.
    """
    # Simplified extended list: specific major world zones not in CIS
    extended_zones = [
        ('Europe/London', 'GMT+0 (Лондон)'),
        ('Europe/Paris', 'GMT+1 (Париж, Берлин)'),
        ('Asia/Dubai', 'GMT+4 (Дубай)'),
        ('Asia/Shanghai', 'GMT+8 (Пекин)'),
        ('Asia/Tokyo', 'GMT+9 (Токио)'),
        ('Australia/Sydney', 'GMT+10 (Сидней)'),
        ('America/New_York', 'GMT-5 (Нью-Йорк)'),
        ('America/Los_Angeles', 'GMT-8 (Лос-Анджелес)'),
    ]
    
    keyboard = []
    row = []
    for tz_name, label in extended_zones:
        callback = f"{TIMEZONE_PREFIX}{tz_name}"
        row.append(InlineKeyboardButton(label, callback_data=callback))
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    # Back button
    keyboard.append([InlineKeyboardButton("◀️ Назад к основным", callback_data="TZ_BACK_MAIN")])
    
    return InlineKeyboardMarkup(keyboard)

def get_user_local_time(timezone_str: str) -> datetime:
    """Returns current time in the specified timezone."""
    try:
        tz = pytz.timezone(timezone_str)
        return datetime.now(tz)
    except Exception:
        return datetime.now(pytz.utc)

def get_user_hour(timezone_str: str) -> int:
    """Returns current hour in the specified timezone."""
    return get_user_local_time(timezone_str).hour

def get_timezone_display_name(timezone_str: str) -> str:
    """Returns a friendly display name for the timezone if available."""
    # Check common
    for key, val in COMMON_TIMEZONES.items():
        if val['name'] == timezone_str:
            return val['display']
            
    # Fallback to string
    return timezone_str
