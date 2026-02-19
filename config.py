import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY") 
# Prioritize DATABASE_URL (for Railway) then fallback to DATABASE_PATH or default SQLite
DATABASE_PATH = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PATH", "data/weather_bot.db")

# Migration logic: if old db exists in root and NOT in data/, move it (ONLY FOR SQLITE)
if not DATABASE_PATH.startswith("postgres"):
    if DATABASE_PATH == "data/weather_bot.db" and os.path.exists("weather_bot.db") and not os.path.exists("data/weather_bot.db"):
        if not os.path.exists("data"):
            os.makedirs("data", exist_ok=True)
        import shutil
        try:
            shutil.copy2("weather_bot.db", "data/weather_bot.db")
            # Keep old one for safety as backup, or rename it
            os.rename("weather_bot.db", "weather_bot.db.bak")
        except Exception:
            pass

    # Ensure directory exists if it's a file path
    if not DATABASE_PATH.startswith("sqlite"):
        db_dir = os.path.dirname(os.path.abspath(DATABASE_PATH))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ADMIN_ID = os.getenv("ADMIN_ID") # Add this to .env to see bot stats

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL),
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Validate critical API keys
if not TELEGRAM_BOT_TOKEN or len(TELEGRAM_BOT_TOKEN) < 20:
    logger.warning("⚠️ TELEGRAM_BOT_TOKEN is missing or invalid. Bot features will not work.")

if not WEATHERAPI_KEY or len(WEATHERAPI_KEY) < 10:
    logger.warning("⚠️ WEATHERAPI_KEY is missing or invalid. Weather features will not work.")

logger.info("✅ Configuration loaded successfully.")
