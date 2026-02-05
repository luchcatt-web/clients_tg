# YClients + Telegram Интеграция

Система для отправки напоминаний о записях из YClients через Telegram и двусторонней связи с клиентами.

## Возможности

✅ **Автоматические напоминания**
- За 24 часа до визита
- За 2 часа до визита

✅ **Уведомления в реальном времени**
- Подтверждение новой записи
- Уведомление об отмене
- Изменения в записи

✅ **Двусторонняя связь**
- Клиенты могут отвечать на напоминания
- История переписки сохраняется в БД
- Виджет для просмотра переписки в YClients

## Установка

### 1. Клонируйте репозиторий
```bash
cd ~/тг\ рассылка
```

### 2. Создайте виртуальное окружение
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

### 4. Настройте конфигурацию

Создайте файл `.env`:

```env
# Telegram настройки
# Получите на https://my.telegram.org/apps
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+79991234567

# YClients настройки
# Получите в личном кабинете YClients -> Настройки -> Интеграции -> API
YCLIENTS_PARTNER_TOKEN=ваш_партнерский_токен
YCLIENTS_USER_TOKEN=ваш_пользовательский_токен
YCLIENTS_COMPANY_ID=123456

# Webhook настройки
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000
WEBHOOK_SECRET=ваш_секретный_ключ

# Настройки напоминаний (в минутах до визита)
REMINDER_BEFORE_24H=1440
REMINDER_BEFORE_2H=120
```

## Получение токенов

### Telegram API
1. Перейдите на https://my.telegram.org/apps
2. Войдите в свой аккаунт
3. Создайте новое приложение
4. Скопируйте `api_id` и `api_hash`

### YClients API
1. Войдите в YClients как администратор
2. Перейдите в **Настройки → Интеграции → API**
3. Включите API и скопируйте токены
4. Company ID найдёте в URL личного кабинета: `https://yclients.com/company/XXXXXX/`

## Запуск

### Обычный запуск
```bash
python main.py
```

При первом запуске Telegram запросит код подтверждения.

### Запуск в фоне (Linux)
```bash
nohup python main.py > logs.txt 2>&1 &
```

### Запуск через systemd
Создайте файл `/etc/systemd/system/yclients-telegram.service`:

```ini
[Unit]
Description=YClients Telegram Integration
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/тг рассылка
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable yclients-telegram
sudo systemctl start yclients-telegram
```

## Настройка Webhook в YClients

1. Откройте YClients → **Настройки → Интеграции → Webhooks**
2. Добавьте URL: `http://ваш_домен:8000/webhook/yclients`
3. Выберите события:
   - `records.create` - новая запись
   - `records.update` - изменение записи
   - `records.delete` - отмена записи

> **Важно:** Для работы webhook ваш сервер должен быть доступен из интернета. Используйте nginx как reverse proxy или сервисы типа ngrok для тестирования.

## Виджет переписки для YClients

Для отображения переписки в карточке клиента используйте iframe:

```html
<iframe 
  src="http://ваш_домен:8000/api/conversations/{client_id}/html"
  width="100%" 
  height="400"
  frameborder="0">
</iframe>
```

Или получайте данные через API:
```
GET http://ваш_домен:8000/api/conversations/{client_id}
```

## Структура проекта

```
тг рассылка/
├── main.py              # Точка входа
├── config.py            # Конфигурация
├── telegram_client.py   # Telegram userbot
├── yclients_api.py      # YClients API
├── database.py          # База данных
├── scheduler.py         # Планировщик напоминаний
├── webhook_server.py    # Webhook сервер
├── requirements.txt     # Зависимости
├── .env                 # Конфигурация (создать вручную)
└── data/
    └── reminders.db     # SQLite база данных
```

## API Endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/` | Проверка работоспособности |
| GET | `/health` | Health check |
| POST | `/webhook/yclients` | Webhook от YClients |
| GET | `/api/conversations/{client_id}` | История переписки (JSON) |
| GET | `/api/conversations/{client_id}/html` | История переписки (HTML) |

## Настройка напоминаний

По умолчанию напоминания отправляются:
- За 24 часа до визита (`REMINDER_BEFORE_24H=1440`)
- За 2 часа до визита (`REMINDER_BEFORE_2H=120`)

Измените значения в `.env` для настройки времени.

## Troubleshooting

### Telegram не находит пользователя по номеру
- Убедитесь, что у клиента есть Telegram
- Номер телефона должен быть в международном формате
- Клиент должен разрешить поиск по номеру в настройках приватности

### FloodWait ошибки
Telegram ограничивает частоту запросов. Система автоматически ждёт и повторяет попытку.

### Webhook не получает события
- Проверьте доступность сервера из интернета
- Убедитесь, что URL указан правильно в YClients
- Проверьте логи на наличие ошибок

## Лицензия

MIT

