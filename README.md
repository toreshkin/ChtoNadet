# 🌤 Telegram Weather Bot (v3.0 - Enhanced)

Smart weather bot with analytics, advanced insights, and proactive notifications.

## ✨ New Features (v3.0)
*   **� Analytics & Insights**:
    *   Compare today's weather with yesterday ("Today is 5°C warmer").
    *   Weekly temperature trend graphs with emojis.
    *   Activity recommendations (Best time for a walk, picnic, drying clothes).
    *   Air Quality Index (AQI) with health recommendations.
    *   UV Index alerts and protection advice.
*   **🔔 Smart Notifications**:
    *   **Rain Alert**: Warns you 1 hour before rain starts.
    *   **Temp Change**: Alerts on drastic temperature drops/rises.
    *   **Severe Weather**: Storm and wind warnings.
    *   **Morning Summary**: Includes daily focus (UV, umbrella need).
    *   **Perfect Weather**: Notification when conditions are ideal for activities.
*   **🎨 Rich UX**:
    *   Beautiful HTML-formatted cards with "Mood" icons.
    *   Interactive Hourly Forecast buttons.
    *   Quick action buttons (Refresh, Details, Stats).
    *   Visual progress bars and clear layouts.
*   **⚙️ Advanced Settings**:
    *   Granular notification control (toggle Rain, UV, AQI alerts separately).
    *   Multiple cities support with "Primary" city selection.
    *   Personalized naming and sensitivity settings.

## 🛠 Installation

1.  Clone repository.
2.  Create venv: `python -m venv venv`
3.  Install: `pip install -r requirements.txt`
4.  Configure `.env` with `TELEGRAM_BOT_TOKEN` and `WEATHERAPI_KEY`.
5.  Run: `python main.py`

## 🤖 Usage

### Start
Send `/start`. The bot will guide you through setting your Name, Timezone, and City.

### Main Menu
*   **🌤 Weather Now**: Detailed card with current temp, feels like, wind, humidity, UV, AQI, and next 3 forecast blocks (Morning/Day/Evening).
*   **⚙️ Settings**:
    *   **Notifications**: Toggle specific alerts (Rain, UV, Storm, etc.).
    *   **Cities**: Manage multiple locations.
    *   **Timezone/Time**: Adjust when you receive daily reports.
*   **📊 Statistics**: View weekly temperature trends.

## 📁 Structure
*   `main.py`: Bot entry point, handlers, and UI logic.
*   `analytics.py`: **[NEW]** Logic for comparisons, trends, and smart insights.
*   `smart_alerts.py`: **[NEW]** Background jobs for Rain/UV/Storm alerts.
*   `scheduler.py`: Job queue management.
*   `weather.py`: WeatherAPI client (Forecast, AQI, Alerts).
*   `database.py`: SQLite storage (Users, Cities, History, Preferences).
*   `keyboards.py`: Inline keyboard layouts.
