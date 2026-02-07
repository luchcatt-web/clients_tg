"""
Webhook сервер для получения событий из YClients
Позволяет реагировать на новые записи, отмены и изменения в реальном времени
+ Scheduler для напоминаний за 24ч и 1ч
"""
import hashlib
import hmac
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import config
from database import db
from telegram_client import telegram
from yclients_api import yclients
from templates import (
    msg_booking_created, msg_booking_changed, msg_booking_cancelled,
    msg_confirmation_24h, msg_reminder_1h
)
from bot_checker import get_bot_client_chat_id, send_via_bot


app = FastAPI(title="YClients Telegram Integration", version="1.0.0")

# Scheduler для напоминаний
scheduler = AsyncIOScheduler()


# === Инициализация Telegram и Scheduler при старте ===
@app.on_event("startup")
async def startup_event():
    """Запуск Telegram клиента и scheduler при старте сервера"""
    await db.init()
    await db.init_records_tracking()
    await telegram.start()
    
    # Запускаем scheduler для напоминаний
    scheduler.add_job(check_reminders, 'interval', minutes=5, id='check_reminders')
    scheduler.start()
    
    print("✅ Telegram клиент запущен!")
    print("✅ Scheduler напоминаний запущен (проверка каждые 5 минут)")


@app.on_event("shutdown")
async def shutdown_event():
    """Остановка Telegram клиента и scheduler"""
    scheduler.shutdown()
    await telegram.stop()


async def check_reminders():
    """Проверка и отправка напоминаний за 24ч и 1ч"""
    try:
        now = datetime.now()
        print(f"⏰ Проверка напоминаний: {now.strftime('%H:%M')}")
        
        # Получаем все активные записи из БД
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM known_records WHERE status = 'active'"
            )
            records = await cursor.fetchall()
        
        for record in records:
            record_id = record["record_id"]
            client_phone = record["client_phone"]
            client_name = record["client_name"]
            service_name = record["service_name"]
            staff_name = record["staff_name"]
            record_date = record["record_date"]
            record_time = record["record_time"]
            
            if not client_phone:
                continue
            
            # Парсим дату записи
            try:
                record_datetime = datetime.strptime(f"{record_date} {record_time}", "%Y-%m-%d %H:%M:%S")
            except:
                try:
                    record_datetime = datetime.strptime(f"{record_date} {record_time}", "%Y-%m-%d %H:%M")
                except:
                    continue
            
            # Пропускаем прошедшие записи
            if record_datetime < now:
                continue
            
            time_until = record_datetime - now
            hours_until = time_until.total_seconds() / 3600
            
            # === Напоминание за 24 часа ===
            if 23 <= hours_until <= 25:
                if not await db.is_reminder_sent(record_id, "24h"):
                    print(f"📤 Напоминание 24ч: {client_name} ({record_id})")
                    
                    # Проверяем, есть ли клиент в боте
                    bot_chat_id = await get_bot_client_chat_id(client_phone)
                    
                    if not bot_chat_id:
                        # Клиент НЕ в боте — отправляем через userbot
                        text = msg_confirmation_24h(client_name, service_name, staff_name, record_datetime)
                        result = await telegram.send_message(
                            phone_or_user_id=client_phone,
                            text=text,
                            record_id=record_id
                        )
                        if result:
                            await db.mark_reminder_sent(record_id, "24h", result.id if hasattr(result, 'id') else None)
                            print(f"   ✅ Отправлено через userbot")
                    else:
                        print(f"   ℹ️ Клиент в боте — бот отправит напоминание")
                        await db.mark_reminder_sent(record_id, "24h")
            
            # === Напоминание за 1 час ===
            elif 0.5 <= hours_until <= 1.5:
                if not await db.is_reminder_sent(record_id, "1h"):
                    print(f"📤 Напоминание 1ч: {client_name} ({record_id})")
                    
                    # Проверяем, есть ли клиент в боте
                    bot_chat_id = await get_bot_client_chat_id(client_phone)
                    
                    if not bot_chat_id:
                        # Клиент НЕ в боте — отправляем через userbot
                        text = msg_reminder_1h(client_name, service_name, staff_name, record_datetime)
                        result = await telegram.send_message(
                            phone_or_user_id=client_phone,
                            text=text,
                            record_id=record_id
                        )
                        if result:
                            await db.mark_reminder_sent(record_id, "1h", result.id if hasattr(result, 'id') else None)
                            print(f"   ✅ Отправлено через userbot")
                    else:
                        print(f"   ℹ️ Клиент в боте — бот отправит напоминание")
                        await db.mark_reminder_sent(record_id, "1h")
        
        print(f"   Проверено записей: {len(records)}")
        
    except Exception as e:
        import traceback
        print(f"❌ Ошибка проверки напоминаний: {e}")
        traceback.print_exc()


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Проверка подписи webhook"""
    if not secret:
        return True
    
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


@app.get("/")
async def root():
    """Проверка работоспособности сервера"""
    return {"status": "ok", "service": "YClients Telegram Integration"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/webhook/yclients")
async def yclients_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Обработка webhook от YClients
    """
    body = await request.body()
    
    signature = request.headers.get("X-Yclients-Signature", "")
    if config.WEBHOOK_SECRET and not verify_signature(body, signature, config.WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    print(f"📥 Webhook: {data.get('resource')}.{data.get('status')}")
    
    background_tasks.add_task(process_webhook, data)
    
    return {"status": "accepted"}


async def process_webhook(data: dict):
    """Обработка webhook в фоновом режиме"""
    resource = data.get("resource", "")
    status = data.get("status", "")
    resource_id = data.get("resource_id")
    payload = data.get("data", {})
    
    print(f"🔍 Обработка: resource={resource}, status={status}, id={resource_id}")
    print(f"📋 Payload: {payload}")
    
    try:
        if resource == "record":  # Исправлено: "record" вместо "records"
            await handle_record_event(status, resource_id, payload)
        elif resource == "client":  # Исправлено: "client" вместо "clients"
            await handle_client_event(status, resource_id, payload)
        else:
            print(f"⚠️ Неизвестный resource: {resource}")
    except Exception as e:
        import traceback
        print(f"❌ Ошибка обработки webhook: {e}")
        traceback.print_exc()


async def handle_record_event(status: str, record_id: int, data: dict):
    """Обработка событий записей"""
    
    # Получаем полные данные записи
    try:
        record_data = await yclients.get_record(record_id)
        record = record_data.get("data", data)
    except Exception:
        record = data
    
    # Извлекаем информацию
    client_data = record.get("client") or {}
    client_name = client_data.get("name", "").split()[0] if client_data.get("name") else "Клиент"
    client_phone = client_data.get("phone", "")
    client_id = client_data.get("id")
    
    if not client_phone:
        print(f"⚠️ Запись {record_id}: нет телефона клиента")
        return
    
    services = record.get("services", [])
    service_name = ", ".join([s.get("title", "") for s in services]) or "Услуга"
    
    staff = record.get("staff", {})
    staff_name = staff.get("name", "Мастер")
    
    # Парсим дату - YClients возвращает datetime в ISO формате: 2026-02-06T22:15:00+03:00
    datetime_field = record.get("datetime", "")
    
    print(f"📅 Парсинг даты: datetime={datetime_field}")
    
    try:
        # ISO формат с часовым поясом: 2026-02-06T22:15:00+03:00
        if "T" in str(datetime_field):
            # Убираем часовой пояс и парсим
            dt_str = str(datetime_field).split("+")[0].split("-03:00")[0].split("-00:00")[0]
            record_datetime = datetime.fromisoformat(dt_str)
            print(f"📅 Время записи (ISO): {record_datetime}")
        else:
            # Старый формат: YYYY-MM-DD HH:MM:SS
            date_str = record.get("date", "")
            time_str = str(datetime_field).split(" ")[-1] if datetime_field else "00:00:00"
            record_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            print(f"📅 Время записи: {record_datetime}")
    except Exception as e:
        print(f"⚠️ Ошибка парсинга даты: {e}")
        record_datetime = datetime.now()
        print(f"⚠️ Используем текущее время: {record_datetime}")
    
    # === НОВАЯ ЗАПИСЬ ===
    if status == "create":
        print(f"📝 Новая запись #{record_id}: {client_name}, тел: {client_phone}")
        
        # Сохраняем запись в БД для напоминаний
        await db.save_known_record(
            record_id=record_id,
            client_phone=client_phone,
            client_name=client_name,
            service_name=service_name,
            staff_name=staff_name,
            record_date=record_datetime.strftime("%Y-%m-%d"),
            record_time=record_datetime.strftime("%H:%M:%S"),
            record_hash="",
            status="active"
        )
        print(f"   💾 Запись сохранена в БД для напоминаний")
        
        text = msg_booking_created(client_name, service_name, staff_name, record_datetime)
        
        # Проверяем, есть ли клиент в боте
        bot_chat_id = await get_bot_client_chat_id(client_phone)
        
        if bot_chat_id:
            # Клиент в боте — отправляем через бота
            print(f"🤖 Клиент в боте (chat_id={bot_chat_id}), отправляем через бота")
            result = await send_via_bot(bot_chat_id, text)
            if result:
                print(f"✅ Сообщение отправлено через бота")
            else:
                print(f"⚠️ Ошибка отправки через бота")
        else:
            # Клиент НЕ в боте — отправляем через userbot + ссылка на бота
            if config.BOT_USERNAME:
                text += f"\n\n🤖 Для управления записями подключите бота: @{config.BOT_USERNAME}"
            
            result = await telegram.send_message(
                phone_or_user_id=client_phone,
                text=text,
                record_id=record_id,
                yclients_client_id=client_id
            )
            if result:
                print(f"✅ Сообщение отправлено через userbot клиенту {client_phone}")
            else:
                print(f"⚠️ Не удалось отправить сообщение клиенту {client_phone}")
    
    # === ЗАПИСЬ ОТМЕНЕНА ===
    elif status == "delete" or record.get("deleted"):
        print(f"❌ Запись #{record_id} отменена: {client_name}, тел: {client_phone}")
        
        # Удаляем запись из БД напоминаний
        await db.mark_record_deleted(record_id)
        print(f"   💾 Запись удалена из БД напоминаний")
        
        text = msg_booking_cancelled(client_name, service_name, record_datetime)
        
        # Проверяем, есть ли клиент в боте
        bot_chat_id = await get_bot_client_chat_id(client_phone)
        
        if bot_chat_id:
            print(f"🤖 Клиент в боте, отправляем через бота")
            await send_via_bot(bot_chat_id, text)
        else:
            result = await telegram.send_message(
                phone_or_user_id=client_phone,
                text=text,
                record_id=record_id,
                yclients_client_id=client_id
            )
            if result:
                print(f"✅ Сообщение об отмене отправлено через userbot")
    
    # === ЗАПИСЬ ИЗМЕНЕНА ===
    elif status == "update":
        print(f"📝 Запись #{record_id} изменена: {client_name}, тел: {client_phone}")
        
        # Обновляем запись в БД для напоминаний
        await db.save_known_record(
            record_id=record_id,
            client_phone=client_phone,
            client_name=client_name,
            service_name=service_name,
            staff_name=staff_name,
            record_date=record_datetime.strftime("%Y-%m-%d"),
            record_time=record_datetime.strftime("%H:%M:%S"),
            record_hash="",
            status="active"
        )
        print(f"   💾 Запись обновлена в БД для напоминаний")
        
        text = msg_booking_changed(client_name, service_name, staff_name, record_datetime)
        
        # Проверяем, есть ли клиент в боте
        bot_chat_id = await get_bot_client_chat_id(client_phone)
        
        if bot_chat_id:
            print(f"🤖 Клиент в боте, отправляем через бота")
            await send_via_bot(bot_chat_id, text)
        else:
            result = await telegram.send_message(
                phone_or_user_id=client_phone,
                text=text,
                record_id=record_id,
                yclients_client_id=client_id
            )
            if result:
                print(f"✅ Сообщение об изменении отправлено через userbot")


async def handle_client_event(status: str, client_id: int, data: dict):
    """Обработка событий клиентов"""
    
    if status == "create":
        phone = data.get("phone", "")
        if phone:
            await db.link_client_telegram(
                yclients_client_id=client_id,
                phone=phone
            )
            print(f"👤 Новый клиент #{client_id} добавлен")


# API для просмотра переписки
@app.get("/api/conversations/{client_id}")
async def get_client_conversations(client_id: int, limit: int = 50):
    """Получить историю переписки с клиентом"""
    history = await db.get_conversation_history(client_id, limit)
    return {
        "client_id": client_id,
        "messages": history
    }


@app.get("/api/conversations/{client_id}/html")
async def get_client_conversations_html(client_id: int, limit: int = 50):
    """Получить историю переписки в HTML формате"""
    history = await db.get_conversation_history(client_id, limit)
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 16px;
                background: #f5f5f5;
                margin: 0;
            }
            .chat-container {
                max-width: 500px;
                margin: 0 auto;
            }
            .message {
                padding: 10px 14px;
                border-radius: 16px;
                margin-bottom: 8px;
                max-width: 85%;
                word-wrap: break-word;
                white-space: pre-wrap;
            }
            .outgoing {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin-left: auto;
                border-bottom-right-radius: 4px;
            }
            .incoming {
                background: white;
                color: #333;
                border: 1px solid #e0e0e0;
                border-bottom-left-radius: 4px;
            }
            .time {
                font-size: 11px;
                color: #999;
                margin-top: 4px;
            }
            .outgoing .time {
                color: rgba(255,255,255,0.7);
            }
            .empty {
                text-align: center;
                color: #999;
                padding: 40px;
            }
            .header {
                text-align: center;
                padding: 10px;
                color: #666;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="header">💬 История переписки</div>
    """
    
    if not history:
        html += '<div class="empty">Нет сообщений</div>'
    else:
        for msg in reversed(history):
            direction_class = msg["direction"]
            time_str = msg["created_at"][:16].replace("T", " ") if msg.get("created_at") else ""
            text = msg["message_text"].replace("<", "&lt;").replace(">", "&gt;")
            
            html += f'''
            <div class="message {direction_class}">
                {text}
                <div class="time">{time_str}</div>
            </div>
            '''
    
    html += """
        </div>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


def run_server():
    """Запуск webhook сервера"""
    import uvicorn
    uvicorn.run(
        app,
        host=config.WEBHOOK_HOST,
        port=config.WEBHOOK_PORT
    )
