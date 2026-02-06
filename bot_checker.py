"""
Проверка наличия клиента в Telegram боте
Если клиент подключил бота - уведомления идут через бота
Если нет - через userbot (аккаунт МЕСТО)
"""
import sqlite3
import tempfile
import os
from typing import Optional
import httpx

from config import config


def normalize_phone(phone: str) -> str:
    """Нормализация номера телефона"""
    if not phone:
        return ""
    digits = ''.join(filter(str.isdigit, str(phone)))
    if len(digits) == 10:
        digits = "7" + digits
    elif len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return "+" + digits


async def get_bot_client_chat_id(phone: str) -> Optional[int]:
    """
    Проверить, есть ли клиент в боте по номеру телефона.
    Возвращает telegram_id если найден, None если нет.
    """
    if not config.S3_ACCESS_KEY or not config.S3_BUCKET:
        return None
    
    normalized = normalize_phone(phone)
    
    try:
        # Скачиваем БД бота из S3
        import boto3
        from botocore.config import Config as BotoConfig
        from botocore.exceptions import ClientError
        
        s3 = boto3.client(
            's3',
            endpoint_url=config.S3_ENDPOINT,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            region_name='ru-1',
            config=BotoConfig(signature_version='s3v4')
        )
        
        # Скачиваем во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            tmp_path = tmp.name
        
        s3.download_file(config.S3_BUCKET, 'clients.db', tmp_path)
        
        # Ищем клиента по телефону
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()
        
        # Пробуем разные форматы номера
        phone_variants = [
            normalized,
            normalized[1:] if normalized.startswith('+') else normalized,
            '8' + normalized[2:] if normalized.startswith('+7') else normalized,
        ]
        
        for phone_var in phone_variants:
            cursor.execute(
                "SELECT telegram_id FROM clients WHERE phone_number LIKE ?",
                (f"%{phone_var[-10:]}%",)
            )
            result = cursor.fetchone()
            if result:
                conn.close()
                os.unlink(tmp_path)
                return result[0]
        
        conn.close()
        os.unlink(tmp_path)
        return None
        
    except Exception as e:
        print(f"Ошибка проверки клиента в боте: {e}")
        return None


async def send_via_bot(chat_id: int, text: str) -> bool:
    """Отправить сообщение через бота"""
    if not config.BOT_TOKEN:
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки через бота: {e}")
        return False


def get_bot_link_text() -> str:
    """Текст со ссылкой на бота"""
    return f"\n\n📱 Подключите бота для управления записями:\n👉 @{config.BOT_USERNAME}"

