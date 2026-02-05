#!/bin/bash
# Скрипт обновления с GitHub
# Запуск: bash /opt/yclients-telegram/deploy/update.sh

set -e

cd /opt/yclients-telegram

echo "🔄 Обновление с GitHub..."

# Останавливаем сервис
echo "⏸️ Останавливаем сервис..."
systemctl stop yclients-telegram || true

# Получаем обновления
echo "📥 Получаем изменения..."
git fetch origin
git reset --hard origin/main

# Обновляем зависимости если изменились
echo "📦 Обновляем зависимости..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# Запускаем сервис
echo "▶️ Запускаем сервис..."
systemctl start yclients-telegram

echo ""
echo "✅ Обновление завершено!"
echo ""
systemctl status yclients-telegram --no-pager

