"""
Конфигурация приложения
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram
    TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
    TELEGRAM_SESSION_NAME = "yclients_reminder"
    
    # YClients
    YCLIENTS_PARTNER_TOKEN = os.getenv("YCLIENTS_PARTNER_TOKEN", "")
    YCLIENTS_USER_TOKEN = os.getenv("YCLIENTS_USER_TOKEN", "")
    YCLIENTS_COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID", 0))
    YCLIENTS_APP_ID = int(os.getenv("YCLIENTS_APP_ID", 36592))  # Application ID для чата
    YCLIENTS_API_URL = "https://api.yclients.com/api/v1"
    
    # Webhook
    WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 8000))
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
    
    # Telegram Bot (для клиентов которые подключили бота)
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "Mesto_yclients_bot")
    
    # S3 для проверки БД бота
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
    S3_BUCKET = os.getenv("S3_BUCKET", "")
    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "https://s3.twcstorage.ru")
    
    # Напоминания (в минутах)
    REMINDER_BEFORE_24H = int(os.getenv("REMINDER_BEFORE_24H", 1440))  # 24 часа
    REMINDER_BEFORE_2H = int(os.getenv("REMINDER_BEFORE_2H", 120))     # 2 часа
    
    # База данных
    DATABASE_PATH = "data/reminders.db"


config = Config()

