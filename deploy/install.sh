#!/bin/bash
# Скрипт установки на Ubuntu/Debian сервер
# Запуск: bash install.sh

set -e

echo "🚀 Установка YClients + Telegram интеграции"
echo "==========================================="

# Обновляем систему
echo "📦 Обновление системы..."
sudo apt update && sudo apt upgrade -y

# Устанавливаем Python
echo "🐍 Установка Python..."
sudo apt install -y python3 python3-pip python3-venv git

# Создаём директорию
echo "📁 Создание директории..."
sudo mkdir -p /opt/yclients-telegram
sudo chown $USER:$USER /opt/yclients-telegram

# Копируем файлы (или клонируем)
echo "📋 Копирование файлов..."
cd /opt/yclients-telegram

# Создаём виртуальное окружение
echo "🔧 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
echo "📥 Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Установка завершена!"
echo ""
echo "Следующие шаги:"
echo "1. Скопируйте файлы проекта в /opt/yclients-telegram/"
echo "2. Создайте файл .env с настройками"
echo "3. Запустите: sudo systemctl enable yclients-telegram"
echo "4. Запустите: sudo systemctl start yclients-telegram"

