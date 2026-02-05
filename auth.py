"""
Скрипт для первичной авторизации в Telegram
Запусти один раз: python auth.py
"""
from pyrogram import Client
from config import config

print("🔐 Авторизация в Telegram...")
print(f"📱 Номер телефона: {config.TELEGRAM_PHONE}")
print()

app = Client(
    config.TELEGRAM_SESSION_NAME,
    api_id=config.TELEGRAM_API_ID,
    api_hash=config.TELEGRAM_API_HASH,
    phone_number=config.TELEGRAM_PHONE
)

with app:
    me = app.get_me()
    print()
    print("=" * 40)
    print(f"✅ Авторизация успешна!")
    print(f"👤 Аккаунт: {me.first_name} (@{me.username})")
    print("=" * 40)
    print()
    print("Теперь можешь запустить основную программу:")
    print("  python main.py")

