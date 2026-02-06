# 🌤 Telegram Weather Bot (v3.0)

Smart weather bot with analytics, advanced insights, and proactive notifications.

## ✨ Features

*   **📊 Analytics & Insights**:
    *   Compare today's weather with yesterday ("Today is 5°C warmer").
    *   Weekly temperature trend graphs with emojis.
    *   Activity recommendations based on weather.
    *   Air Quality (AQI) & UV Index alerts.
*   **🔔 Smart Notifications**:
    *   Rain Alert (1h before), Temperature Change, Severe Weather.
    *   Morning Summary with daily focus.
    *   Customizable notification preferences.
*   **🌍 Multi-City Support**:
    *   Add multiple cities and switch between them.
    *   Timezone-aware notifications.
*   **🎨 Rich UX**:
    *   Persistent action buttons on every message (Weather, Stats, Menu).
    *   Mood-based weather icons.
    *   Interactive layouts with inline keyboards.

## 🛠 Installation

1.  Clone repository.
2.  Create venv: `python -m venv venv`
3.  Install: `pip install -r requirements.txt`
4.  Configure `.env` with API keys.
5.  Run: `python main.py`

### API Keys Setup
1.  **Telegram**: Get from @BotFather.
2.  **WeatherAPI**: Get from [weatherapi.com](https://www.weatherapi.com/).

**Env file example:** 
```
TELEGRAM_BOT_TOKEN=your_token_here
WEATHERAPI_KEY=your_key_here
DATABASE_PATH=weather_bot.db
LOG_LEVEL=INFO
```

## 🤖 Usage

### Start
Send `/start`. The bot will guide you through setting your Name, Timezone, and City.

### Main Menu
*   **🌤 Weather Now**: Detailed card with current temp, feels like, wind, humidity, UV, AQI.
*   **⚙️ Settings**: Control notifications, cities, timezone, temperature sensitivity.
*   **📊 Statistics**: View weekly temperature trends and comparisons.

## 📁 Structure
*   `main.py`: Bot entry point and handlers.
*   `analytics.py`: Logic for comparisons and trends.
*   `smart_alerts.py`: Background jobs for Rain/UV/Storm alerts.
*   `database.py`: SQLite storage (Users, Cities, Weather History).
*   `keyboards.py`: Inline keyboard layouts.
*   `scheduler.py`: APScheduler configuration for notifications.
*   `weather.py`: WeatherAPI integration.

## 🚀 Deployment

Recommended platform: **Railway**

1. Connect your GitHub repository
2. Add environment variables in Railway dashboard
3. Deploy automatically on push

## 📝 License

MIT License - feel free to use and modify!
