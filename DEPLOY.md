# 🚀 Деплой на сервер

## Шаг 1: Арендуйте VPS сервер

Рекомендую **Timeweb Cloud** (простой и дешёвый):
1. Зайдите на https://timeweb.cloud
2. Зарегистрируйтесь
3. Создайте сервер:
   - **ОС:** Ubuntu 22.04
   - **Тариф:** Минимальный (1 CPU, 1 GB RAM) — хватит
   - **Цена:** ~200₽/мес

После создания получите:
- IP адрес сервера
- Пароль root

---

## Шаг 2: Подключитесь к серверу

На Mac откройте Терминал и введите:
```bash
ssh root@ВАШ_IP_АДРЕС
```

Введите пароль когда спросит.

---

## Шаг 3: Установите зависимости

```bash
# Обновляем систему
apt update && apt upgrade -y

# Устанавливаем Python
apt install -y python3 python3-pip python3-venv git unzip
```

---

## Шаг 4: Загрузите проект на сервер

### Вариант А: Через SCP (с вашего Mac)

На Mac в новом окне терминала:
```bash
# Архивируем проект
cd ~
zip -r tg-yclients.zip "тг рассылка" -x "*.session*" -x "venv/*" -x "__pycache__/*" -x "*.log"

# Загружаем на сервер
scp tg-yclients.zip root@ВАШ_IP:/root/
```

На сервере:
```bash
cd /root
unzip tg-yclients.zip
mv "тг рассылка" /opt/yclients-telegram
cd /opt/yclients-telegram
```

### Вариант Б: Через SFTP (FileZilla)

1. Скачайте FileZilla: https://filezilla-project.org
2. Подключитесь: Host=ВАШ_IP, User=root, Password=ваш_пароль, Port=22
3. Перетащите папку проекта в `/opt/yclients-telegram`

---

## Шаг 5: Настройте проект на сервере

```bash
cd /opt/yclients-telegram

# Создаём виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Шаг 6: Создайте файл .env

```bash
nano .env
```

Вставьте (измените на свои данные):
```
TELEGRAM_API_ID=19691308
TELEGRAM_API_HASH=e5070da3a0874c79ad81d18e4cb3df99
TELEGRAM_PHONE=+79038690354

YCLIENTS_PARTNER_TOKEN=befz68u9gpj6n3ut5zrs
YCLIENTS_USER_TOKEN=3f51da75bd76560950ed70e1a3fbae27
YCLIENTS_COMPANY_ID=1540716

WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000
WEBHOOK_SECRET=
```

Сохраните: `Ctrl+X`, потом `Y`, потом `Enter`

---

## Шаг 7: Авторизуйтесь в Telegram

```bash
cd /opt/yclients-telegram
source venv/bin/activate
python auth.py
```

Введите код из Telegram когда спросит.

---

## Шаг 8: Настройте автозапуск

```bash
# Копируем файл сервиса
cp deploy/yclients-telegram.service /etc/systemd/system/

# Активируем
systemctl daemon-reload
systemctl enable yclients-telegram
systemctl start yclients-telegram
```

---

## Шаг 9: Проверьте что работает

```bash
# Статус
systemctl status yclients-telegram

# Логи
journalctl -u yclients-telegram -f

# Или
tail -f /var/log/yclients-telegram.log
```

---

## 🎉 Готово!

Система будет работать 24/7 и автоматически перезапускаться при сбоях.

---

## Полезные команды

```bash
# Перезапустить
systemctl restart yclients-telegram

# Остановить
systemctl stop yclients-telegram

# Посмотреть логи
journalctl -u yclients-telegram -f

# Обновить код
cd /opt/yclients-telegram
systemctl stop yclients-telegram
# ... загрузите новые файлы ...
systemctl start yclients-telegram
```

---

## Настройка Webhook (для мгновенных уведомлений)

Чтобы получать события из YClients в реальном времени:

1. В YClients: **Настройки → Интеграции → Webhooks**
2. URL: `http://ВАШ_IP:8000/webhook/yclients`
3. Выберите события: records.create, records.update, records.delete

---

## Проблемы?

### Telegram не авторизуется
- Убедитесь что .env содержит правильные API_ID и API_HASH
- Удалите файл `*.session` и авторизуйтесь заново

### Ошибка 401 от YClients
- Проверьте токены в .env
- Убедитесь что приложение подключено к филиалу

### Сервис не запускается
- Проверьте логи: `journalctl -u yclients-telegram -n 50`
- Проверьте права: `chown -R root:root /opt/yclients-telegram`

