"""
Запрос нового кода
"""
import asyncio
from pyrogram import Client
from config import config

async def get_code():
    app = Client(
        config.TELEGRAM_SESSION_NAME,
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
    )
    
    await app.connect()
    
    sent_code = await app.send_code(config.TELEGRAM_PHONE)
    
    print(f"✅ Код отправлен!")
    print(f"📱 phone_code_hash: {sent_code.phone_code_hash}")
    
    # Сохраняем hash для следующего шага
    with open("code_hash.txt", "w") as f:
        f.write(sent_code.phone_code_hash)
    
    await app.disconnect()

asyncio.run(get_code())

