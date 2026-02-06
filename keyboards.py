from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Constants for Callback Data
WEATHER_NOW = "weather_now"
SETTINGS = "settings"
STATS = "stats"
HELP = "help"
BACK_TO_MENU = "back_menu"

CHANGE_CITY = "change_city"
ADD_CITY = "add_city"
LIST_CITIES = "list_cities"
REMOVE_CITY = "remove_city"

CHANGE_TIME = "change_time"
CHANGE_SENSITIVITY = "change_sensitivity"
CHANGE_NAME = "change_name"
CHANGE_TIMEZONE = "change_timezone"
TOGGLE_NOTIFICATIONS = "toggle_notif"
NOTIFICATION_PREFS = "notif_prefs"
REFRESH_WEATHER = "refresh_weather"
WEATHER_DETAILS = "weather_details"
WEATHER_STATS = "weather_stats"
ANALYZE_CLOTHING = "analyze_clothing"

SENSITIVITY_COLD = "sens_cold"
SENSITIVITY_NORMAL = "sens_normal"
SENSITIVITY_HOT = "sens_hot"

# New standard action buttons
def get_standard_action_buttons():
    """Returns the persistent action row."""
    return [
        [
            InlineKeyboardButton("🌤️ Погода", callback_data=WEATHER_NOW),
            InlineKeyboardButton("📊 Статистика", callback_data=STATS),
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data=SETTINGS),
            InlineKeyboardButton("📱 Меню", callback_data=BACK_TO_MENU),
        ]
    ]

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🌤️ Погода сейчас", callback_data=WEATHER_NOW)],
        [InlineKeyboardButton("⚙️ Настройки", callback_data=SETTINGS), InlineKeyboardButton("📊 Статистика", callback_data=STATS)],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data=HELP)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_weather_action_buttons():
    """Quick actions for weather message."""
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data=REFRESH_WEATHER)],
        [InlineKeyboardButton("📊 Детали", callback_data=WEATHER_DETAILS),
         InlineKeyboardButton("📈 Статистика", callback_data=WEATHER_STATS)],
         [InlineKeyboardButton("⚙️ Настройки", callback_data=SETTINGS)]
    ]
    keyboard.append([InlineKeyboardButton("📱 Меню", callback_data=BACK_TO_MENU)])
    return InlineKeyboardMarkup(keyboard)

def get_photo_analysis_buttons(photo_file_id):
    keyboard = [
        [
            InlineKeyboardButton("💾 Сохранить в гардероб", callback_data=f"save_clothing_{photo_file_id}"),
            InlineKeyboardButton("🔄 Анализ снова", callback_data="analyze_again")
        ],
        # Standard buttons
        *get_standard_action_buttons()
    ]
    return InlineKeyboardMarkup(keyboard)

def get_notification_settings_keyboard(prefs: dict):
    def btn(text, key):
        state = "✅" if prefs.get(key, True) else "❌"
        return InlineKeyboardButton(f"{state} {text}", callback_data=f"toggle_{key}")

    keyboard = [
        [btn("Ежедневный прогноз", "daily_forecast")],
        [btn("Дождь", "rain_alerts"), btn("Температура", "temp_change_alerts")],
        [btn("UV индекс", "uv_alerts"), btn("Качество воздуха", "air_quality_alerts")],
        [btn("Шторм", "severe_weather_alerts"), btn("Идеальная погода", "perfect_weather_alerts")],
        [InlineKeyboardButton("◀️ Назад", callback_data=SETTINGS)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(notifications_on=True, alerts_on=True):
    notif_icon = "🔔" if notifications_on else "🔕"
    
    keyboard = [
        # Quick Actions
        [InlineKeyboardButton(f"{notif_icon} Настроить уведомления", callback_data=NOTIFICATION_PREFS)],
        [InlineKeyboardButton("🏙️ Мои города", callback_data=LIST_CITIES)],
        
        # Toggles/Settings
        [InlineKeyboardButton("🌍 Часовой пояс", callback_data=CHANGE_TIMEZONE), 
         InlineKeyboardButton("🕐 Время", callback_data=CHANGE_TIME)],
        
        [InlineKeyboardButton("🌡️ Чувствительность", callback_data=CHANGE_SENSITIVITY),
         InlineKeyboardButton("✏️ Имя", callback_data=CHANGE_NAME)],
         
        [InlineKeyboardButton("◀️ Назад в меню", callback_data=BACK_TO_MENU)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cities_keyboard(cities, current_primary_id):
    keyboard = []
    for city in cities:
        prefix = "⭐ " if city['id'] == current_primary_id or city['is_primary'] else ""
        keyboard.append([InlineKeyboardButton(f"{prefix}{city['city_name']}", callback_data=f"view_city_{city['id']}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить город", callback_data=ADD_CITY)])
    keyboard.append([InlineKeyboardButton("🗑️ Удалить город", callback_data=REMOVE_CITY)])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=SETTINGS)])
    return InlineKeyboardMarkup(keyboard)

def get_sensitivity_keyboard():
    keyboard = [
        [InlineKeyboardButton("❄️ Мерзляк", callback_data=SENSITIVITY_COLD)],
        [InlineKeyboardButton("😊 Нормальный", callback_data=SENSITIVITY_NORMAL)],
        [InlineKeyboardButton("🔥 Жаркий", callback_data=SENSITIVITY_HOT)],
        [InlineKeyboardButton("◀️ Назад", callback_data=SETTINGS)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_time_keyboard():
    keyboard = [
        [InlineKeyboardButton("06:00", callback_data="time_06:00"), InlineKeyboardButton("07:00", callback_data="time_07:00")],
        [InlineKeyboardButton("08:00", callback_data="time_08:00"), InlineKeyboardButton("09:00", callback_data="time_09:00")],
        [InlineKeyboardButton("10:00", callback_data="time_10:00"), InlineKeyboardButton("✏️ Свое время", callback_data="time_custom")],
        [InlineKeyboardButton("◀️ Назад", callback_data=SETTINGS)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=BACK_TO_MENU)]])

def get_main_reply_keyboard():
    """
    Persistent Reply Keyboard for quick access to main features.
    Shows at the bottom of the chat.
    """
    keyboard = [
        [KeyboardButton("🌤 Погода"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("⚙️ Настройки"), KeyboardButton("ℹ️ Помощь")],
        [KeyboardButton("📍 Моя геолокация", request_location=True)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

