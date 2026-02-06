"""
Модуль базы данных для хранения напоминаний и переписок
"""
import aiosqlite
import os
from datetime import datetime
from typing import Optional
from config import config


class Database:
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        
    async def init(self):
        """Инициализация базы данных"""
        # Создаём директорию если не существует
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица для отслеживания отправленных напоминаний
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sent_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER NOT NULL,
                    reminder_type TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    telegram_message_id INTEGER,
                    UNIQUE(record_id, reminder_type)
                )
            """)
            
            # Таблица для связи клиентов YClients с Telegram
            await db.execute("""
                CREATE TABLE IF NOT EXISTS client_telegram_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    yclients_client_id INTEGER UNIQUE NOT NULL,
                    telegram_user_id INTEGER,
                    telegram_username TEXT,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для хранения переписки
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    yclients_client_id INTEGER NOT NULL,
                    record_id INTEGER,
                    direction TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    telegram_message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для ожидающих подтверждения записей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pending_confirmations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER NOT NULL,
                    telegram_user_id INTEGER NOT NULL,
                    yclients_client_id INTEGER,
                    record_datetime TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(record_id, telegram_user_id)
                )
            """)
            
            await db.commit()
    
    async def is_reminder_sent(self, record_id: int, reminder_type: str) -> bool:
        """Проверить, было ли уже отправлено напоминание"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM sent_reminders WHERE record_id = ? AND reminder_type = ?",
                (record_id, reminder_type)
            )
            row = await cursor.fetchone()
            return row is not None
    
    async def mark_reminder_sent(
        self, 
        record_id: int, 
        reminder_type: str, 
        telegram_message_id: Optional[int] = None
    ):
        """Отметить напоминание как отправленное"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO sent_reminders 
                   (record_id, reminder_type, telegram_message_id, sent_at) 
                   VALUES (?, ?, ?, ?)""",
                (record_id, reminder_type, telegram_message_id, datetime.now())
            )
            await db.commit()
    
    async def link_client_telegram(
        self, 
        yclients_client_id: int,
        phone: str,
        telegram_user_id: Optional[int] = None,
        telegram_username: Optional[str] = None
    ):
        """Связать клиента YClients с Telegram"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO client_telegram_links 
                   (yclients_client_id, telegram_user_id, telegram_username, phone, updated_at) 
                   VALUES (?, ?, ?, ?, ?)""",
                (yclients_client_id, telegram_user_id, telegram_username, phone, datetime.now())
            )
            await db.commit()
    
    async def get_telegram_by_client_id(self, yclients_client_id: int) -> Optional[dict]:
        """Получить Telegram данные по ID клиента YClients"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM client_telegram_links WHERE yclients_client_id = ?",
                (yclients_client_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_client_by_telegram(self, telegram_user_id: int) -> Optional[dict]:
        """Получить клиента YClients по Telegram ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM client_telegram_links WHERE telegram_user_id = ?",
                (telegram_user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_client_by_phone(self, phone: str) -> Optional[dict]:
        """Получить клиента по номеру телефона"""
        # Нормализуем телефон
        normalized = ''.join(filter(str.isdigit, phone))
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM client_telegram_links WHERE phone LIKE ?",
                (f"%{normalized[-10:]}%",)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def save_conversation(
        self,
        yclients_client_id: int,
        direction: str,
        message_text: str,
        record_id: Optional[int] = None,
        telegram_message_id: Optional[int] = None
    ):
        """Сохранить сообщение переписки"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO conversations 
                   (yclients_client_id, record_id, direction, message_text, telegram_message_id) 
                   VALUES (?, ?, ?, ?, ?)""",
                (yclients_client_id, record_id, direction, message_text, telegram_message_id)
            )
            await db.commit()
    
    async def get_conversation_history(
        self, 
        yclients_client_id: int, 
        limit: int = 50
    ) -> list:
        """Получить историю переписки с клиентом"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM conversations 
                   WHERE yclients_client_id = ? 
                   ORDER BY created_at DESC LIMIT ?""",
                (yclients_client_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def add_pending_confirmation(
        self,
        record_id: int,
        telegram_user_id: int,
        yclients_client_id: int,
        record_datetime: str
    ):
        """Добавить запись в ожидание подтверждения"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO pending_confirmations 
                   (record_id, telegram_user_id, yclients_client_id, record_datetime) 
                   VALUES (?, ?, ?, ?)""",
                (record_id, telegram_user_id, yclients_client_id, record_datetime)
            )
            await db.commit()
    
    async def get_pending_confirmation(self, telegram_user_id: int) -> Optional[dict]:
        """Получить ожидающую подтверждения запись для пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM pending_confirmations 
                   WHERE telegram_user_id = ? 
                   ORDER BY created_at DESC LIMIT 1""",
                (telegram_user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def remove_pending_confirmation(self, record_id: int, telegram_user_id: int):
        """Удалить запись из ожидающих подтверждения"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM pending_confirmations WHERE record_id = ? AND telegram_user_id = ?",
                (record_id, telegram_user_id)
            )
            await db.commit()
    
    async def init_records_tracking(self):
        """Инициализация таблицы для отслеживания записей (polling)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS known_records (
                    id INTEGER PRIMARY KEY,
                    record_id INTEGER UNIQUE NOT NULL,
                    client_phone TEXT,
                    client_name TEXT,
                    service_name TEXT,
                    staff_name TEXT,
                    record_date TEXT,
                    record_time TEXT,
                    status TEXT DEFAULT 'active',
                    hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def get_known_record(self, record_id: int) -> Optional[dict]:
        """Получить известную запись"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM known_records WHERE record_id = ?",
                (record_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def save_known_record(
        self,
        record_id: int,
        client_phone: str,
        client_name: str,
        service_name: str,
        staff_name: str,
        record_date: str,
        record_time: str,
        record_hash: str,
        status: str = "active"
    ):
        """Сохранить известную запись"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO known_records 
                   (record_id, client_phone, client_name, service_name, staff_name, 
                    record_date, record_time, hash, status, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record_id, client_phone, client_name, service_name, staff_name,
                 record_date, record_time, record_hash, status, datetime.now())
            )
            await db.commit()
    
    async def get_all_active_record_ids(self) -> set:
        """Получить все ID активных записей"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT record_id FROM known_records WHERE status = 'active'"
            )
            rows = await cursor.fetchall()
            return {row[0] for row in rows}
    
    async def mark_record_deleted(self, record_id: int):
        """Отметить запись как удалённую"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE known_records SET status = 'deleted', updated_at = ? WHERE record_id = ?",
                (datetime.now(), record_id)
            )
            await db.commit()


# Синглтон
db = Database()

