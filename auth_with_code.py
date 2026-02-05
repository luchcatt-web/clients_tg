"""
Авторизация с кодом
"""
import asyncio
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from config import config

async def auth():
    app = Client(
        config.TELEGRAM_SESSION_NAME,
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
    )
    
    await app.connect()
    
    # Отправляем код
    sent_code = await app.send_code(config.TELEGRAM_PHONE)
    
    # Вводим код
    code = "91447"
    
    try:
        await app.sign_in(config.TELEGRAM_PHONE, sent_code.phone_code_hash, code)
    except SessionPasswordNeeded:
        print("⚠️ Нужен пароль двухфакторной аутентификации!")
        print("Напиши мне свой 2FA пароль")
        await app.disconnect()
        return
    
    me = await app.get_me()
    print(f"✅ Авторизация успешна! Аккаунт: {me.first_name}")
    
    await app.disconnect()

asyncio.run(auth())

