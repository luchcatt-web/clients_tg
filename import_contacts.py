"""
Массовый импорт контактов из YClients в Telegram
Запуск: python import_contacts.py
"""
import asyncio
from datetime import datetime

from config import config
from yclients_api import yclients
from telegram_client import telegram


async def get_all_clients():
    """Получить всех клиентов из YClients"""
    all_clients = []
    page = 1
    count = 200  # Максимум за раз
    
    print("📥 Загружаем клиентов из YClients...")
    
    while True:
        try:
            result = await yclients.get_clients(page=page, count=count)
            
            if not result.get("success") or not result.get("data"):
                break
            
            clients = result["data"]
            all_clients.extend(clients)
            
            total = result.get("meta", {}).get("total_count", len(all_clients))
            print(f"   Страница {page}: загружено {len(clients)} клиентов (всего: {len(all_clients)}/{total})")
            
            if len(clients) < count:
                break
            
            page += 1
            await asyncio.sleep(0.5)  # Пауза между запросами
            
        except Exception as e:
            print(f"❌ Ошибка на странице {page}: {e}")
            break
    
    print(f"✅ Всего загружено: {len(all_clients)} клиентов")
    return all_clients


async def import_contacts_to_telegram(clients: list):
    """Импортировать контакты в Telegram"""
    from pyrogram.raw.functions.contacts import ImportContacts
    from pyrogram.raw.types import InputPhoneContact
    
    # Фильтруем клиентов с телефонами
    contacts_to_import = []
    
    for client in clients:
        phone = client.get("phone", "")
        name = client.get("name", "Клиент")
        
        if not phone:
            continue
        
        # Нормализуем телефон
        normalized = telegram.normalize_phone(phone)
        
        # Разделяем имя на части
        name_parts = name.split() if name else ["Клиент"]
        first_name = name_parts[0] if name_parts else "Клиент"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        contacts_to_import.append({
            "phone": normalized,
            "first_name": first_name,
            "last_name": last_name
        })
    
    print(f"\n📱 Импортируем {len(contacts_to_import)} контактов в Telegram...")
    
    # Telegram позволяет импортировать до 100 контактов за раз
    batch_size = 100
    imported_count = 0
    
    for i in range(0, len(contacts_to_import), batch_size):
        batch = contacts_to_import[i:i + batch_size]
        
        input_contacts = [
            InputPhoneContact(
                client_id=idx,
                phone=c["phone"],
                first_name=c["first_name"],
                last_name=c["last_name"]
            )
            for idx, c in enumerate(batch)
        ]
        
        try:
            result = await telegram.app.invoke(
                ImportContacts(contacts=input_contacts)
            )
            
            imported = len(result.users) if result.users else 0
            imported_count += imported
            
            print(f"   Партия {i//batch_size + 1}: {imported} из {len(batch)} найдено в Telegram")
            
            await asyncio.sleep(1)  # Пауза между партиями
            
        except Exception as e:
            print(f"   ❌ Ошибка партии {i//batch_size + 1}: {e}")
    
    return imported_count, len(contacts_to_import)


async def main():
    print("=" * 60)
    print("🚀 Импорт контактов YClients → Telegram")
    print("=" * 60)
    print(f"⏰ Начало: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Запускаем Telegram клиент
    print("📱 Подключение к Telegram...")
    await telegram.start()
    print("✅ Telegram подключен!")
    print()
    
    # Получаем клиентов
    clients = await get_all_clients()
    
    if not clients:
        print("❌ Нет клиентов для импорта")
        await telegram.stop()
        return
    
    # Импортируем контакты
    imported, total = await import_contacts_to_telegram(clients)
    
    print()
    print("=" * 60)
    print(f"✅ ГОТОВО!")
    print(f"   Всего клиентов: {len(clients)}")
    print(f"   С телефонами: {total}")
    print(f"   Найдено в Telegram: {imported}")
    print(f"   Процент покрытия: {imported/total*100:.1f}%")
    print("=" * 60)
    print()
    print("💡 Теперь сообщения будут доходить этим клиентам!")
    print("   Клиенты без Telegram или с закрытыми настройками")
    print("   не будут получать сообщения — это ограничение Telegram.")
    print()
    
    await telegram.stop()


if __name__ == "__main__":
    asyncio.run(main())

