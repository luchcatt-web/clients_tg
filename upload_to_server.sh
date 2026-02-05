#!/bin/bash
# Скрипт для загрузки проекта на сервер
# Использование: ./upload_to_server.sh IP_АДРЕС
# Пример: ./upload_to_server.sh 123.45.67.89

if [ -z "$1" ]; then
    echo "❌ Укажите IP адрес сервера"
    echo "Использование: ./upload_to_server.sh IP_АДРЕС"
    echo "Пример: ./upload_to_server.sh 123.45.67.89"
    exit 1
fi

SERVER_IP=$1
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Загрузка проекта на сервер $SERVER_IP"
echo "========================================="

# Создаём архив без лишних файлов
echo "📦 Создание архива..."
cd "$PROJECT_DIR"
zip -r /tmp/yclients-telegram.zip . \
    -x "*.session*" \
    -x "*.session-journal" \
    -x "venv/*" \
    -x "__pycache__/*" \
    -x "*.pyc" \
    -x "*.log" \
    -x "data/*.db" \
    -x ".git/*" \
    -x "*.zip"

# Загружаем на сервер
echo "📤 Загрузка на сервер..."
scp /tmp/yclients-telegram.zip root@$SERVER_IP:/tmp/

# Распаковываем на сервере
echo "📂 Распаковка на сервере..."
ssh root@$SERVER_IP << 'ENDSSH'
mkdir -p /opt/yclients-telegram
cd /opt/yclients-telegram
unzip -o /tmp/yclients-telegram.zip
rm /tmp/yclients-telegram.zip

# Если venv не существует - создаём
if [ ! -d "venv" ]; then
    echo "🔧 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Устанавливаем зависимости
source venv/bin/activate
pip install -r requirements.txt

echo ""
echo "✅ Файлы загружены в /opt/yclients-telegram"
ENDSSH

# Удаляем локальный архив
rm /tmp/yclients-telegram.zip

echo ""
echo "✅ Готово!"
echo ""
echo "Следующие шаги на сервере:"
echo "1. ssh root@$SERVER_IP"
echo "2. cd /opt/yclients-telegram"
echo "3. nano .env  # создайте файл с настройками"
echo "4. source venv/bin/activate && python auth.py  # авторизация в Telegram"
echo "5. bash deploy/setup_service.sh  # настройка автозапуска"

