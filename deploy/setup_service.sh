#!/bin/bash
# Настройка systemd сервиса
# Запуск: sudo bash setup_service.sh

set -e

echo "🔧 Настройка systemd сервиса..."

# Копируем файл сервиса
sudo cp yclients-telegram.service /etc/systemd/system/

# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable yclients-telegram

# Запускаем
sudo systemctl start yclients-telegram

echo ""
echo "✅ Сервис настроен!"
echo ""
echo "Полезные команды:"
echo "  sudo systemctl status yclients-telegram  - статус"
echo "  sudo systemctl restart yclients-telegram - перезапуск"
echo "  sudo systemctl stop yclients-telegram    - остановка"
echo "  sudo journalctl -u yclients-telegram -f  - логи"
echo "  sudo tail -f /var/log/yclients-telegram.log - логи файл"

