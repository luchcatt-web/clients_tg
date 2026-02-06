"""
YClients + Telegram интеграция
Отправка напоминаний о записях и двусторонняя связь с клиентами

Запуск: python main.py
"""
import asyncio
import sys
from datetime import datetime

from config import config
from database import db
from telegram_client import telegram
from scheduler import reminder_scheduler
from yclients_api import yclients
from templates import msg_confirmed
from datetime import datetime


async def handle_incoming_message(message):
    """
    Обработчик входящих сообщений от клиентов
    Обрабатывает подтверждения записей (+) и сохраняет переписку
    """
    user_id = message.from_user.id
    text = (message.text or "").strip()
    
    # Ищем клиента в БД
    client_link = await db.get_client_by_telegram(user_id)
    
    # === Проверяем подтверждение записи ===
    if text in ["+", "да", "Да", "ДА", "yes", "Yes", "YES", "подтверждаю", "Подтверждаю"]:
        pending = await db.get_pending_confirmation(user_id)
        
        if pending:
            record_id = pending["record_id"]
            yclients_client_id = pending["yclients_client_id"]
            record_datetime_str = pending["record_datetime"]
            
            try:
                # Подтверждаем запись в YClients
                await yclients.confirm_record(record_id)
                
                # Удаляем из ожидающих
                await db.remove_pending_confirmation(record_id, user_id)
                
                # Парсим дату для ответа
                try:
                    record_datetime = datetime.fromisoformat(record_datetime_str)
                except:
                    record_datetime = datetime.now()
                
                # Получаем имя клиента
                client_name = "Клиент"
                if client_link:
                    try:
                        client_data = await yclients.get_client(yclients_client_id)
                        if client_data.get("success"):
                            client_name = client_data["data"].get("name", "").split()[0] or "Клиент"
                    except:
                        pass
                
                # Отправляем подтверждение
                confirm_text = msg_confirmed(client_name, record_datetime)
                await telegram.send_message(
                    phone_or_user_id=user_id,
                    text=confirm_text,
                    record_id=record_id,
                    yclients_client_id=yclients_client_id
                )
                
                print(f"✅ Запись #{record_id} подтверждена клиентом!")
                return
                
            except Exception as e:
                print(f"❌ Ошибка подтверждения записи: {e}")
    
    # === Сохраняем сообщение в историю ===
    if client_link:
        await db.save_conversation(
            yclients_client_id=client_link["yclients_client_id"],
            direction="incoming",
            message_text=text,
            telegram_message_id=message.id
        )
        
        print(f"💬 Сообщение от клиента #{client_link['yclients_client_id']}: {text[:50]}...")
    else:
        print(f"💬 Сообщение от неизвестного пользователя {user_id}: {text[:50]}...")


async def main():
    """Главная функция"""
    print("=" * 50)
    print("🚀 Запуск YClients + Telegram интеграции")
    print("=" * 50)
    
    # Проверяем конфигурацию
    errors = []
    
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        errors.append("❌ Не заданы TELEGRAM_API_ID и TELEGRAM_API_HASH")
    
    if not config.YCLIENTS_PARTNER_TOKEN or not config.YCLIENTS_USER_TOKEN:
        errors.append("❌ Не заданы токены YClients API")
    
    if not config.YCLIENTS_COMPANY_ID:
        errors.append("❌ Не задан YCLIENTS_COMPANY_ID")
    
    if errors:
        print("\n⚠️ Ошибки конфигурации:")
        for err in errors:
            print(f"  {err}")
        print("\nСоздайте файл .env по примеру .env.example")
        sys.exit(1)
    
    # Инициализация БД
    print("\n📦 Инициализация базы данных...")
    await db.init()
    
    # Запуск Telegram клиента
    print("\n📱 Подключение к Telegram...")
    telegram.add_message_handler(handle_incoming_message)
    await telegram.start()
    
    # Проверка подключения к YClients
    print("\n🔗 Проверка подключения к YClients...")
    try:
        staff = await yclients.get_staff()
        if staff.get("success"):
            print(f"   ✅ Подключено! Сотрудников: {len(staff.get('data', []))}")
        else:
            print("   ⚠️ Не удалось получить данные (проверьте токены)")
    except Exception as e:
        print(f"   ❌ Ошибка подключения: {e}")
    
    # Первичная синхронизация записей (polling)
    print("\n🔍 Первичная синхронизация записей...")
    await db.init_records_tracking()
    await reminder_scheduler.initial_sync()
    
    # Запуск планировщика напоминаний
    print("\n⏰ Запуск планировщика...")
    reminder_scheduler.start()
    
    print("\n" + "=" * 50)
    print("✅ Система запущена и готова к работе!")
    print("=" * 50)
    print("\n📊 Режим работы: POLLING (без webhook)")
    print("   - Проверка новых записей: каждые 60 секунд")
    print("   - Напоминания: каждые 5 минут")
    print("   - За 24 часа до визита — подтверждение")
    print("   - За 1 час до визита — напоминание")
    print("\nДля остановки нажмите Ctrl+C\n")
    
    # Бесконечный цикл работы
    try:
        # Ждём пока не будет сигнала остановки
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 Завершение работы...")
        reminder_scheduler.stop()
        await telegram.stop()
        print("👋 До свидания!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
