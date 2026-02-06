"""
Webhook сервер для получения событий из YClients
Позволяет реагировать на новые записи, отмены и изменения в реальном времени
"""
import hashlib
import hmac
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from config import config
from database import db
from telegram_client import telegram
from yclients_api import yclients
from templates import msg_booking_created, msg_booking_changed, msg_booking_cancelled


app = FastAPI(title="YClients Telegram Integration", version="1.0.0")


# === Инициализация Telegram при старте ===
@app.on_event("startup")
async def startup_event():
    """Запуск Telegram клиента при старте сервера"""
    await db.init()
    await telegram.start()
    print("✅ Telegram клиент запущен!")


@app.on_event("shutdown")
async def shutdown_event():
    """Остановка Telegram клиента"""
    await telegram.stop()


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
    
    # Парсим дату
    date_str = record.get("date", "")
    time_str = record.get("datetime", "").split(" ")[-1] if record.get("datetime") else "00:00:00"
    
    try:
        record_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        record_datetime = datetime.now()
    
    # === НОВАЯ ЗАПИСЬ ===
    if status == "create":
        print(f"📝 Новая запись #{record_id}: {client_name}, тел: {client_phone}")
        
        text = msg_booking_created(client_name, service_name, staff_name, record_datetime)
        
        # Добавляем ссылку на бота
        if config.BOT_USERNAME:
            text += f"\n\n🤖 Для управления записями подключите бота: @{config.BOT_USERNAME}"
        
        result = await telegram.send_message(
            phone_or_user_id=client_phone,
            text=text,
            record_id=record_id,
            yclients_client_id=client_id
        )
        if result:
            print(f"✅ Сообщение отправлено клиенту {client_phone}")
        else:
            print(f"⚠️ Не удалось отправить сообщение клиенту {client_phone}")
    
    # === ЗАПИСЬ ОТМЕНЕНА ===
    elif status == "delete" or record.get("deleted"):
        print(f"❌ Запись #{record_id} отменена: {client_name}, тел: {client_phone}")
        
        text = msg_booking_cancelled(client_name, service_name, record_datetime)
        result = await telegram.send_message(
            phone_or_user_id=client_phone,
            text=text,
            record_id=record_id,
            yclients_client_id=client_id
        )
        if result:
            print(f"✅ Сообщение об отмене отправлено")
    
    # === ЗАПИСЬ ИЗМЕНЕНА ===
    elif status == "update":
        print(f"📝 Запись #{record_id} изменена: {client_name}, тел: {client_phone}")
        
        text = msg_booking_changed(client_name, service_name, staff_name, record_datetime)
        result = await telegram.send_message(
            phone_or_user_id=client_phone,
            text=text,
            record_id=record_id,
            yclients_client_id=client_id
        )
        if result:
            print(f"✅ Сообщение об изменении отправлено")


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
