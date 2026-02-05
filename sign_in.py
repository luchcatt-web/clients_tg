"""
Вход с кодом
"""
import asyncio
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from config import config

async def sign_in():
    app = Client(
        config.TELEGRAM_SESSION_NAME,
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
    )
    
    await app.connect()
    
    # Читаем сохранённый hash
    with open("code_hash.txt", "r") as f:
        phone_code_hash = f.read().strip()
    
    code = "10632"
    
    try:
        await app.sign_in(config.TELEGRAM_PHONE, phone_code_hash, code)
        me = await app.get_me()
        print(f"✅ Авторизация успешна! Аккаунт: {me.first_name} (@{me.username})")
    except SessionPasswordNeeded:
        print("⚠️ Нужен пароль двухфакторной аутентификации!")
        print("Напиши мне свой 2FA пароль")
    
    await app.disconnect()

asyncio.run(sign_in())

