"""
Быстрая авторизация - запрос и ввод кода в одном сеансе
"""
import asyncio
import sys
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from config import config

CODE = sys.argv[1] if len(sys.argv) > 1 else None

async def quick_auth():
    if not CODE:
        print("Использование: python quick_auth.py ТВОЙ_КОД")
        return
        
    app = Client(
        config.TELEGRAM_SESSION_NAME,
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
    )
    
    await app.connect()
    
    print("📱 Запрашиваю код...")
    sent_code = await app.send_code(config.TELEGRAM_PHONE)
    
    print(f"✅ Код отправлен! Ввожу: {CODE}")
    
    try:
        await app.sign_in(config.TELEGRAM_PHONE, sent_code.phone_code_hash, CODE)
        me = await app.get_me()
        print()
        print("=" * 40)
        print(f"✅ УСПЕХ! Аккаунт: {me.first_name} (@{me.username})")
        print("=" * 40)
    except SessionPasswordNeeded:
        print()
        print("⚠️ У тебя включена двухфакторная аутентификация!")
        print("Напиши мне свой 2FA пароль от Telegram")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    await app.disconnect()

asyncio.run(quick_auth())

