"""
Модуль для работы с YClients API
https://api.yclients.com/
"""
import httpx
from datetime import datetime, timedelta
from typing import Optional
from config import config


class YClientsAPI:
    def __init__(self):
        self.base_url = config.YCLIENTS_API_URL
        self.partner_token = config.YCLIENTS_PARTNER_TOKEN
        self.user_token = config.YCLIENTS_USER_TOKEN
        self.company_id = config.YCLIENTS_COMPANY_ID
        
    def _get_headers(self) -> dict:
        """Заголовки для API запросов"""
        return {
            "Authorization": f"Bearer {self.partner_token}, User {self.user_token}",
            "Accept": "application/vnd.api.v2+json",
            "Content-Type": "application/json"
        }
    
    async def get_records(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        count: int = 100
    ) -> dict:
        """
        Получить записи за период
        """
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=7)
            
        params = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "page": page,
            "count": count
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/records/{self.company_id}",
                headers=self._get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_record(self, record_id: int) -> dict:
        """Получить информацию о конкретной записи"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/record/{self.company_id}/{record_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def get_client(self, client_id: int) -> dict:
        """Получить информацию о клиенте"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/client/{self.company_id}/{client_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def get_clients(self, page: int = 1, count: int = 100) -> dict:
        """Получить список клиентов"""
        params = {"page": page, "count": count}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/clients/{self.company_id}",
                headers=self._get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def search_clients(self, phone: str = None, name: str = None) -> dict:
        """Поиск клиентов по телефону или имени"""
        data = {}
        if phone:
            data["phone"] = phone
        if name:
            data["name"] = name
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/clients/{self.company_id}/search",
                headers=self._get_headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def get_staff(self) -> dict:
        """Получить список сотрудников"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/staff/{self.company_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def get_services(self) -> dict:
        """Получить список услуг"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/services/{self.company_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def get_upcoming_records(self, hours_ahead: int = 48) -> list:
        """
        Получить ближайшие записи для напоминаний
        """
        start_date = datetime.now()
        end_date = start_date + timedelta(hours=hours_ahead)
        
        result = await self.get_records(start_date, end_date)
        
        if not result.get("success"):
            return []
        
        records = result.get("data", [])
        upcoming = []
        
        for record in records:
            # Пропускаем отменённые записи
            if record.get("deleted"):
                continue
            
            # Парсим дату и время записи
            record_datetime_str = f"{record.get('date')} {record.get('datetime', '').split(' ')[-1]}"
            try:
                record_datetime = datetime.strptime(record_datetime_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, IndexError):
                continue
            
            # Добавляем информацию о времени до визита
            time_until = record_datetime - datetime.now()
            record["minutes_until"] = int(time_until.total_seconds() / 60)
            record["record_datetime"] = record_datetime
            
            upcoming.append(record)
        
        return sorted(upcoming, key=lambda x: x["record_datetime"])
    
    async def add_comment_to_record(self, record_id: int, comment: str) -> dict:
        """Добавить комментарий к записи (для хранения переписки)"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/record/{self.company_id}/{record_id}",
                headers=self._get_headers(),
                json={"comment": comment}
            )
            response.raise_for_status()
            return response.json()
    
    async def confirm_record(self, record_id: int) -> dict:
        """Подтвердить запись клиентом (attendance_status = 1)"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/record/{self.company_id}/{record_id}",
                headers=self._get_headers(),
                json={"attendance": 1}  # 1 = клиент подтвердил
            )
            response.raise_for_status()
            return response.json()


# Синглтон для использования в других модулях
yclients = YClientsAPI()

