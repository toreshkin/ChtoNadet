from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Constants for Callback Data
WEATHER_NOW = "weather_now"
SETTINGS = "settings"
STATS = "stats"
HELP = "help"

CHANGE_CITY = "change_city"
ADD_CITY = "add_city"
LIST_CITIES = "list_cities"
REMOVE_CITY = "remove_city"

CHANGE_TIME = "change_time"
CHANGE_SENSITIVITY = "change_sensitivity"
CHANGE_NAME = "change_name"
TOGGLE_NOTIFICATIONS = "toggle_notif"
TOGGLE_ALERTS = "toggle_alerts"
BACK_TO_MENU = "back_menu"

SENSITIVITY_COLD = "sens_cold"
SENSITIVITY_NORMAL = "sens_normal"
SENSITIVITY_HOT = "sens_hot"

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🌤️ Погода сейчас", callback_data=WEATHER_NOW)],
        [InlineKeyboardButton("⚙️ Настройки", callback_data=SETTINGS), InlineKeyboardButton("📊 Статистика", callback_data=STATS)],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data=HELP)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(notifications_on=True, alerts_on=True):
    notif_icon = "🔔" if notifications_on else "🔕"
    alert_icon = "⚠️" if alerts_on else "🔇"
    
    keyboard = [
        [InlineKeyboardButton("🏙️ Мои города", callback_data=LIST_CITIES)],
        [InlineKeyboardButton("🕐 Время уведомлений", callback_data=CHANGE_TIME)],
        [InlineKeyboardButton("🌡️ Чувствительность", callback_data=CHANGE_SENSITIVITY)],
        [InlineKeyboardButton("✏️ Изменить имя", callback_data=CHANGE_NAME)],
        [InlineKeyboardButton(f"{notif_icon} Уведомления", callback_data=TOGGLE_NOTIFICATIONS)],
        [InlineKeyboardButton(f"{alert_icon} Алерты", callback_data=TOGGLE_ALERTS)],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data=BACK_TO_MENU)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cities_keyboard(cities, current_primary_id):
    """
    Generates a list of cities.
    cities: list of dicts {'id', 'city_name', 'is_primary'}
    """
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
