import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY") 
DATABASE_PATH = os.getenv("DATABASE_PATH", "weather_bot.db")
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
    raise ValueError("❌ Invalid or missing TELEGRAM_BOT_TOKEN. Please check your .env file.")

if not WEATHERAPI_KEY or len(WEATHERAPI_KEY) < 10:
    raise ValueError("❌ Invalid or missing WEATHERAPI_KEY. Please check your .env file.")

logger.info("✅ Configuration loaded successfully.")
