# 🌤 Telegram Weather Bot (v3.1 - AI Powered)

Smart weather bot with analytics, advanced insights, and proactive notifications. Now with Google Gemini AI for wardrobe analysis!

## ✨ New Features (v3.1)
*   **🤖 AI Clothing Analysis**:
    *   Send a photo of any clothing item.
    *   Bot detects type, material, and warmth using Gemini Vision.
    *   Compares with current weather to give a strict "Go/No-Go" verdict.
    *   Save items to your virtual wardrobe.
*   **📊 Analytics & Insights**:
    *   Compare today's weather with yesterday ("Today is 5°C warmer").
    *   Weekly temperature trend graphs with emojis.
    *   Activity recommendations.
    *   Air Quality (AQI) & UV Index alerts.
*   **🔔 Smart Notifications**:
    *   Rain Alert (1h before), Temp Change, Severe Weather.
    *   Morning Summary with daily focus.
*   **🎨 Rich UX**:
    *   Persistent action buttons on every message (Weather, Stats, Menu).
    *   Mood-based weather icons.
    *   Interactive layouts.

## 🛠 Installation

1.  Clone repository.
2.  Create venv: `python -m venv venv`
3.  Install: `pip install -r requirements.txt`
4.  Configure `.env` with API keys.
5.  Run: `python main.py`

### API Keys Setup
1.  **Telegram**: Get from @BotFather.
2.  **WeatherAPI**: Get from [weatherapi.com](https://www.weatherapi.com/).
3.  **Google Gemini**: 
    - Go to [Google AI Studio](https://ai.google.dev/).
    - "Get API key" -> Create key.
    - Free tier allows 15 requests/minute.

**Env file example:** 
```
TELEGRAM_BOT_TOKEN=...
WEATHERAPI_KEY=...
GEMINI_API_KEY=...
```

## 🤖 Usage

### Start
Send `/start`. The bot will guide you through setting your Name, Timezone, and City.

### AI Analysis
Simply send a **photo** to the bot. It will analyze usage suitability for today's weather.

### Main Menu
*   **🌤 Weather Now**: Detailed card with current temp, feels like, wind, humidity, UV, AQI.
*   **⚙️ Settings**: Control notifications, cities, timezone.
*   **📊 Statistics**: View weekly temperature trends.

## 📁 Structure
*   `main.py`: Bot entry point, handlers (including Photo).
*   `ai_analysis.py`: **[NEW]** Google Gemini integration.
*   `analytics.py`: Logic for comparisons and trends.
*   `smart_alerts.py`: Background jobs for Rain/UV/Storm alerts.
*   `database.py`: SQLite storage (Users, Cities, Wardrobe).
*   `keyboards.py`: Inline keyboard layouts.
