"""
Telegram клиент (userbot) для отправки напоминаний
Использует Pyrogram для работы от имени вашего аккаунта
"""
import asyncio
import re
from datetime import datetime
from typing import Optional, Callable, Union
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserNotMutualContact, PeerIdInvalid

from config import config
from database import db


class TelegramClient:
    def __init__(self):
        self.app = Client(
            config.TELEGRAM_SESSION_NAME,
            api_id=config.TELEGRAM_API_ID,
            api_hash=config.TELEGRAM_API_HASH,
            phone_number=config.TELEGRAM_PHONE
        )
        self.message_handlers = []
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков входящих сообщений"""
        @self.app.on_message(filters.private & filters.incoming)
        async def handle_incoming_message(client: Client, message: Message):
            """Обработка входящих сообщений от клиентов"""
            for handler in self.message_handlers:
                try:
                    await handler(message)
                except Exception as e:
                    print(f"Ошибка в обработчике сообщений: {e}")
    
    def add_message_handler(self, handler: Callable):
        """Добавить обработчик входящих сообщений"""
        self.message_handlers.append(handler)
    
    async def start(self):
        """Запуск клиента"""
        await self.app.start()
        me = await self.app.get_me()
        print(f"✅ Telegram клиент запущен как: {me.first_name} (@{me.username})")
    
    async def stop(self):
        """Остановка клиента"""
        try:
            await self.app.stop()
        except Exception:
            pass
        print("🛑 Telegram клиент остановлен")
    
    def normalize_phone(self, phone: str) -> str:
        """Нормализация номера телефона"""
        # Оставляем только цифры
        digits = ''.join(filter(str.isdigit, phone))
        
        # Добавляем код страны если нужно
        if len(digits) == 10:
            digits = "7" + digits
        elif len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        
        return "+" + digits
    
    async def find_user_by_phone(self, phone: str) -> Optional[dict]:
        """
        Поиск пользователя Telegram по номеру телефона
        """
        normalized = self.normalize_phone(phone)
        
        try:
            # Пробуем получить контакт по телефону
            contacts = await self.app.get_contacts()
            
            for contact in contacts:
                if contact.phone_number:
                    contact_phone = self.normalize_phone(contact.phone_number)
                    if contact_phone == normalized or contact_phone.endswith(normalized[-10:]):
                        return {
                            "user_id": contact.id,
                            "username": contact.username,
                            "first_name": contact.first_name,
                            "last_name": contact.last_name,
                            "phone": contact.phone_number
                        }
            
            # Если не нашли в контактах, пробуем импортировать с разными форматами
            from pyrogram.raw.functions.contacts import ImportContacts
            from pyrogram.raw.types import InputPhoneContact
            
            # Пробуем разные форматы номера
            digits = normalized.replace("+", "")
            phone_formats = [
                normalized,           # +79532781888
                digits,               # 79532781888
                "8" + digits[1:],     # 89532781888
                digits[-10:],         # 9532781888 (без кода страны)
            ]
            
            for phone_format in phone_formats:
                print(f"📥 Импортируем контакт: {phone_format}")
                
                try:
                    result = await self.app.invoke(
                        ImportContacts(
                            contacts=[InputPhoneContact(
                                client_id=0,
                                phone=phone_format,
                                first_name="Клиент",
                                last_name="YClients"
                            )]
                        )
                    )
                    
                    if result.users:
                        user = result.users[0]
                        print(f"✅ Контакт импортирован: {user.first_name} (ID: {user.id})")
                        return {
                            "user_id": user.id,
                            "username": user.username,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "phone": normalized
                        }
                except Exception as e:
                    print(f"   Формат {phone_format}: не найден")
                    continue
            
            print(f"⚠️ Пользователь с номером {normalized} не найден ни в одном формате")
            return None
            
        except Exception as e:
            print(f"Ошибка поиска пользователя по телефону {phone}: {e}")
            return None
    
    async def send_message(
        self, 
        phone_or_user_id: Union[str, int],
        text: str,
        record_id: Optional[int] = None,
        yclients_client_id: Optional[int] = None
    ) -> Optional[Message]:
        """
        Отправить сообщение клиенту
        """
        try:
            # Если передан телефон, ищем пользователя
            if isinstance(phone_or_user_id, str):
                user_info = await self.find_user_by_phone(phone_or_user_id)
                if not user_info:
                    print(f"⚠️ Пользователь с телефоном {phone_or_user_id} не найден в Telegram")
                    return None
                user_id = user_info["user_id"]
                
                # Сохраняем связь в БД
                if yclients_client_id:
                    await db.link_client_telegram(
                        yclients_client_id=yclients_client_id,
                        phone=phone_or_user_id,
                        telegram_user_id=user_info["user_id"],
                        telegram_username=user_info.get("username")
                    )
            else:
                user_id = phone_or_user_id
            
            # Отправляем сообщение
            message = await self.app.send_message(
                chat_id=user_id,
                text=text
            )
            
            # Сохраняем в историю переписки
            if yclients_client_id:
                await db.save_conversation(
                    yclients_client_id=yclients_client_id,
                    direction="outgoing",
                    message_text=text,
                    record_id=record_id,
                    telegram_message_id=message.id
                )
            
            print(f"✉️ Сообщение отправлено пользователю {user_id}")
            return message
            
        except FloodWait as e:
            print(f"⏳ FloodWait: ждём {e.value} секунд...")
            await asyncio.sleep(e.value)
            return await self.send_message(phone_or_user_id, text, record_id, yclients_client_id)
            
        except UserNotMutualContact:
            print(f"⚠️ Пользователь {phone_or_user_id} не в контактах")
            return None
            
        except PeerIdInvalid:
            print(f"⚠️ Неверный ID пользователя: {phone_or_user_id}")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения: {e}")
            return None
    
    async def send_reminder(
        self,
        phone: str,
        client_name: str,
        service_name: str,
        staff_name: str,
        record_datetime: datetime,
        record_id: int,
        yclients_client_id: int,
        reminder_type: str = "24h"
    ) -> Optional[Message]:
        """
        Отправить напоминание о записи
        """
        # Форматируем дату и время
        date_str = record_datetime.strftime("%d.%m.%Y")
        time_str = record_datetime.strftime("%H:%M")
        
        if reminder_type == "24h":
            text = f"""📅 Напоминание о записи!

Здравствуйте, {client_name}!

Напоминаем, что завтра у вас запланирован визит:

🕐 Дата: {date_str}
⏰ Время: {time_str}
💇 Услуга: {service_name}
👤 Мастер: {staff_name}

Если у вас изменились планы, пожалуйста, сообщите заранее.

Ждём вас! 💫"""
        else:  # 2h
            text = f"""⏰ Скоро ваш визит!

Здравствуйте, {client_name}!

Через 2 часа вас ждут:

🕐 Время: {time_str}
💇 Услуга: {service_name}
👤 Мастер: {staff_name}

До встречи! 🌟"""
        
        return await self.send_message(
            phone_or_user_id=phone,
            text=text,
            record_id=record_id,
            yclients_client_id=yclients_client_id
        )
    
    async def send_booking_confirmation(
        self,
        phone: str,
        client_name: str,
        service_name: str,
        staff_name: str,
        record_datetime: datetime,
        record_id: int,
        yclients_client_id: int
    ) -> Optional[Message]:
        """
        Отправить подтверждение записи
        """
        date_str = record_datetime.strftime("%d.%m.%Y")
        time_str = record_datetime.strftime("%H:%M")
        
        text = f"""✅ Запись подтверждена!

Здравствуйте, {client_name}!

Ваша запись успешно создана:

🕐 Дата: {date_str}
⏰ Время: {time_str}
💇 Услуга: {service_name}
👤 Мастер: {staff_name}

Если хотите изменить или отменить запись — напишите нам.

Ждём вас! 🎉"""
        
        return await self.send_message(
            phone_or_user_id=phone,
            text=text,
            record_id=record_id,
            yclients_client_id=yclients_client_id
        )
    
    async def send_cancellation_notice(
        self,
        phone: str,
        client_name: str,
        service_name: str,
        record_datetime: datetime,
        record_id: int,
        yclients_client_id: int
    ) -> Optional[Message]:
        """
        Уведомление об отмене записи
        """
        date_str = record_datetime.strftime("%d.%m.%Y")
        time_str = record_datetime.strftime("%H:%M")
        
        text = f"""❌ Запись отменена

Здравствуйте, {client_name}!

Ваша запись отменена:

🕐 Дата: {date_str}
⏰ Время: {time_str}
💇 Услуга: {service_name}

Если хотите записаться на другое время — напишите нам!"""
        
        return await self.send_message(
            phone_or_user_id=phone,
            text=text,
            record_id=record_id,
            yclients_client_id=yclients_client_id
        )


# Синглтон
telegram = TelegramClient()

