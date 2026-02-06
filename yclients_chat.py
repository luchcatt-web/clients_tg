"""
Интеграция с чатом YClients
Отправляет сообщения из Telegram в боковую панель чата YClients
"""
import httpx
import logging
from config import config

logger = logging.getLogger(__name__)


class YClientsChat:
    """
    Класс для работы с чатом YClients через API
    Документация: https://support.yclients.com/67-767-771-773
    """
    
    def __init__(self):
        self.api_url = "https://api.yclients.com/marketplace/application/new_message"
        self.app_id = config.YCLIENTS_APP_ID
        self.salon_id = config.YCLIENTS_COMPANY_ID
        self.partner_token = config.YCLIENTS_PARTNER_TOKEN
        self.user_token = config.YCLIENTS_USER_TOKEN
    
    async def send_message_to_yclients(
        self, 
        phone: str, 
        message: str, 
        name: str = None
    ) -> bool:
        """
        Отправляет сообщение в боковую панель чата YClients
        
        Args:
            phone: Номер телефона клиента (от кого сообщение)
            message: Текст сообщения
            name: Имя клиента (опционально)
        
        Returns:
            True если успешно, False в случае ошибки
        """
        if not self.app_id or not self.salon_id:
            logger.warning("YClients Chat: app_id или salon_id не настроены")
            return False
        
        # Нормализуем номер телефона
        normalized_phone = self._normalize_phone(phone)
        
        headers = {
            "Accept": "application/vnd.api.v2+json",
            "Authorization": f"Bearer {self.partner_token}, User {self.user_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "application_id": self.app_id,
            "salon_id": self.salon_id,
            "phone_from": normalized_phone,
            "message": message,
        }
        
        if name:
            data["name"] = name
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Сообщение отправлено в чат YClients от {normalized_phone}")
                    return True
                else:
                    logger.error(f"❌ Ошибка отправки в чат YClients: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Исключение при отправке в чат YClients: {e}")
            return False
    
    def _normalize_phone(self, phone: str) -> str:
        """Нормализует номер телефона"""
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 10:
            digits = "7" + digits
        elif len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        return "+" + digits


# Глобальный экземпляр
yclients_chat = YClientsChat()

