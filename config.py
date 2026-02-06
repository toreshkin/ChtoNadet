import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY") 
DATABASE_PATH = os.getenv("DATABASE_PATH", "weather_bot.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

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

if not TELEGRAM_BOT_TOKEN or not WEATHERAPI_KEY:
    logger.warning("TELEGRAM_BOT_TOKEN or WEATHERAPI_KEY not found in environment variables.")
