from telegram.ext import ApplicationBuilder
from config import TELEGRAM_BOT_TOKEN

def create_application():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in config")
        
    return ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
