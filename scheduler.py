"""
Планировщик напоминаний
Периодически проверяет записи и отправляет напоминания
"""
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import config
from database import db
from yclients_api import yclients
from telegram_client import telegram
from templates import (
    msg_confirmation_24h, msg_reminder_1h, msg_review_request,
    msg_lost_client_21, msg_lost_client_35, msg_lost_client_65
)


class ReminderScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def check_and_send_reminders(self):
        """
        Проверить ближайшие записи и отправить напоминания
        """
        print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Проверка записей для напоминаний...")
        
        try:
            # Получаем записи на ближайшие 48 часов
            records = await yclients.get_upcoming_records(hours_ahead=48)
            
            for record in records:
                await self._process_record(record)
                
        except Exception as e:
            print(f"❌ Ошибка при проверке записей: {e}")
    
    async def _process_record(self, record: dict):
        """Обработка отдельной записи"""
        record_id = record.get("id")
        minutes_until = record.get("minutes_until", 0)
        
        # Получаем данные для напоминания
        client_data = record.get("client", {})
        client_name = client_data.get("name", "").split()[0] if client_data.get("name") else "Клиент"
        client_phone = client_data.get("phone", "")
        client_id = client_data.get("id")
        
        if not client_phone:
            return
        
        # Получаем услуги
        services = record.get("services", [])
        service_name = ", ".join([s.get("title", "") for s in services]) or "Услуга"
        
        # Получаем мастера
        staff = record.get("staff", {})
        staff_name = staff.get("name", "Мастер")
        
        record_datetime = record.get("record_datetime")
        
        # === Подтверждение записи за 24 часа ===
        if 1380 <= minutes_until <= 1500:  # 23-25 часов
            if not await db.is_reminder_sent(record_id, "24h"):
                print(f"📤 Отправляем запрос подтверждения: {client_name}")
                
                text = msg_confirmation_24h(client_name, service_name, staff_name, record_datetime)
                message = await telegram.send_message(
                    phone_or_user_id=client_phone,
                    text=text,
                    record_id=record_id,
                    yclients_client_id=client_id
                )
                
                if message:
                    await db.mark_reminder_sent(record_id, "24h", message.id)
                    
                    # Сохраняем ожидание подтверждения
                    user_info = await telegram.find_user_by_phone(client_phone)
                    if user_info:
                        await db.add_pending_confirmation(
                            record_id=record_id,
                            telegram_user_id=user_info["user_id"],
                            yclients_client_id=client_id,
                            record_datetime=record_datetime.isoformat()
                        )
                    
                    print(f"✅ Запрос подтверждения отправлен: {client_name}")
        
        # === Напоминание за 1 час ===
        if 45 <= minutes_until <= 75:  # 45-75 минут
            if not await db.is_reminder_sent(record_id, "1h"):
                print(f"📤 Отправляем напоминание за 1ч: {client_name}")
                
                text = msg_reminder_1h(client_name, service_name, staff_name, record_datetime)
                message = await telegram.send_message(
                    phone_or_user_id=client_phone,
                    text=text,
                    record_id=record_id,
                    yclients_client_id=client_id
                )
                
                if message:
                    await db.mark_reminder_sent(record_id, "1h", message.id)
                    print(f"✅ Напоминание за 1ч отправлено: {client_name}")
    
    async def check_completed_visits(self):
        """Проверка завершённых визитов для запроса отзыва"""
        print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Проверка завершённых визитов...")
        
        try:
            # Получаем записи за последние 3 часа
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=3)
            
            result = await yclients.get_records(start_date, end_date)
            
            if not result.get("success"):
                return
            
            records = result.get("data", [])
            
            for record in records:
                if record.get("deleted"):
                    continue
                
                record_id = record.get("id")
                
                # Проверяем, прошла ли запись
                record_datetime_str = f"{record.get('date')} {record.get('datetime', '').split(' ')[-1]}"
                try:
                    record_datetime = datetime.strptime(record_datetime_str, "%Y-%m-%d %H:%M:%S")
                except (ValueError, IndexError):
                    continue
                
                # Если запись была 1-3 часа назад — отправляем запрос отзыва
                hours_ago = (datetime.now() - record_datetime).total_seconds() / 3600
                
                if 1 <= hours_ago <= 3:
                    if not await db.is_reminder_sent(record_id, "review"):
                        client_data = record.get("client", {})
                        client_name = client_data.get("name", "").split()[0] if client_data.get("name") else "Клиент"
                        client_phone = client_data.get("phone", "")
                        client_id = client_data.get("id")
                        
                        if not client_phone:
                            continue
                        
                        services = record.get("services", [])
                        service_name = ", ".join([s.get("title", "") for s in services]) or "Услуга"
                        staff = record.get("staff", {})
                        staff_name = staff.get("name", "Мастер")
                        
                        print(f"📤 Отправляем запрос отзыва: {client_name}")
                        
                        text = msg_review_request(client_name, service_name, staff_name)
                        message = await telegram.send_message(
                            phone_or_user_id=client_phone,
                            text=text,
                            record_id=record_id,
                            yclients_client_id=client_id
                        )
                        
                        if message:
                            await db.mark_reminder_sent(record_id, "review", message.id)
                            print(f"✅ Запрос отзыва отправлен: {client_name}")
                            
        except Exception as e:
            print(f"❌ Ошибка при проверке завершённых визитов: {e}")
    
    async def check_lost_clients(self):
        """Проверка потерянных клиентов"""
        print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Проверка потерянных клиентов...")
        
        try:
            # Получаем всех клиентов
            result = await yclients.get_clients(page=1, count=200)
            
            if not result.get("success"):
                return
            
            clients = result.get("data", [])
            now = datetime.now()
            
            for client in clients:
                client_id = client.get("id")
                client_name = client.get("name", "").split()[0] if client.get("name") else "Клиент"
                client_phone = client.get("phone", "")
                last_visit = client.get("last_visit_date")
                
                if not client_phone or not last_visit:
                    continue
                
                try:
                    last_visit_date = datetime.strptime(last_visit, "%Y-%m-%d")
                except ValueError:
                    continue
                
                days_since = (now - last_visit_date).days
                
                # Потеряшки 21 день (20-22 дня)
                if 20 <= days_since <= 22:
                    reminder_key = f"lost21_{client_id}"
                    if not await db.is_reminder_sent(client_id, reminder_key):
                        print(f"📤 Потеряшка 21 день: {client_name}")
                        
                        text = msg_lost_client_21(client_name)
                        message = await telegram.send_message(
                            phone_or_user_id=client_phone,
                            text=text,
                            yclients_client_id=client_id
                        )
                        
                        if message:
                            await db.mark_reminder_sent(client_id, reminder_key, message.id)
                
                # Потеряшки 35 дней (34-36 дней)
                elif 34 <= days_since <= 36:
                    reminder_key = f"lost35_{client_id}"
                    if not await db.is_reminder_sent(client_id, reminder_key):
                        print(f"📤 Потеряшка 35 дней: {client_name}")
                        
                        text = msg_lost_client_35(client_name)
                        message = await telegram.send_message(
                            phone_or_user_id=client_phone,
                            text=text,
                            yclients_client_id=client_id
                        )
                        
                        if message:
                            await db.mark_reminder_sent(client_id, reminder_key, message.id)
                
                # Потеряшки 65 дней (64-66 дней)
                elif 64 <= days_since <= 66:
                    reminder_key = f"lost65_{client_id}"
                    if not await db.is_reminder_sent(client_id, reminder_key):
                        print(f"📤 Потеряшка 65 дней: {client_name}")
                        
                        text = msg_lost_client_65(client_name)
                        message = await telegram.send_message(
                            phone_or_user_id=client_phone,
                            text=text,
                            yclients_client_id=client_id
                        )
                        
                        if message:
                            await db.mark_reminder_sent(client_id, reminder_key, message.id)
                            
        except Exception as e:
            print(f"❌ Ошибка при проверке потерянных клиентов: {e}")
    
    def start(self):
        """Запуск планировщика"""
        if self.is_running:
            return
        
        # Проверяем записи каждые 5 минут
        self.scheduler.add_job(
            self.check_and_send_reminders,
            trigger=IntervalTrigger(minutes=5),
            id="check_reminders",
            name="Проверка напоминаний",
            replace_existing=True
        )
        
        # Проверяем завершённые визиты каждые 30 минут
        self.scheduler.add_job(
            self.check_completed_visits,
            trigger=IntervalTrigger(minutes=30),
            id="check_reviews",
            name="Проверка отзывов",
            replace_existing=True
        )
        
        # Проверяем потерянных клиентов раз в день в 10:00
        self.scheduler.add_job(
            self.check_lost_clients,
            trigger=IntervalTrigger(hours=24),
            id="check_lost",
            name="Проверка потеряшек",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        print("⏰ Планировщик напоминаний запущен")
    
    def stop(self):
        """Остановка планировщика"""
        if not self.is_running:
            return
        
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        print("🛑 Планировщик напоминаний остановлен")
    
    async def run_once(self):
        """Однократная проверка (для отладки)"""
        await self.check_and_send_reminders()


# Синглтон
reminder_scheduler = ReminderScheduler()
