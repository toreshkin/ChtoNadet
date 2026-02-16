import logging
import os

def setup_logging(log_level="INFO"):
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, log_level),
        handlers=[
            logging.FileHandler("bot.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)
