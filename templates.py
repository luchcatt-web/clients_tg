"""
Шаблоны сообщений для рассылки
Аналогичные Бьюти Бот
"""
import random
from datetime import datetime


def get_greeting():
    """Случайное приветствие"""
    greetings = ["Добрый день", "Здравствуйте", "Привет"]
    return random.choice(greetings)


def get_emoji_greeting():
    """Случайное приветствие с эмодзи"""
    options = ["🐱 Добрый день", "🤗 Здравствуйте", "👋 Привет"]
    return random.choice(options)


def format_date(dt: datetime) -> str:
    """Форматирование даты"""
    months = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    return f"{dt.day} {months[dt.month]}"


def format_time(dt: datetime) -> str:
    """Форматирование времени"""
    return dt.strftime("%H:%M")


# ===== ШАБЛОНЫ СООБЩЕНИЙ =====

def msg_booking_created(client_name: str, service: str, staff: str, dt: datetime) -> str:
    """При создании записи"""
    date_str = format_date(dt)
    time_str = format_time(dt)
    
    templates = [
        f"""👋 {client_name}, вы записаны в 💇 МЕСТО на услугу

📅 {date_str} в {time_str}
💇 {service}
👤 Мастер: {staff}

Ждём вас! Если планы изменятся — напишите нам 💬""",

        f"""✅ {client_name}, запись подтверждена!

💇 МЕСТО ждёт вас:
📅 {date_str}
⏰ {time_str}
✨ {service}
👤 {staff}

До встречи! 🌟"""
    ]
    return random.choice(templates)


def msg_confirmation_24h(client_name: str, service: str, staff: str, dt: datetime) -> str:
    """Подтверждение записи за 24 часа"""
    date_str = format_date(dt)
    time_str = format_time(dt)
    greeting = get_emoji_greeting()
    
    templates = [
        f"""{greeting}, {client_name}! 

Это 💇 МЕСТО — напоминаем о вашем визите завтра:

📅 {date_str}
⏰ {time_str}
✨ {service}
👤 Мастер: {staff}

✅ Для подтверждения записи отправьте +
❌ Если не сможете прийти — напишите нам""",

        f"""📅 {client_name}, подтвердите запись!

Завтра в {time_str} ждём вас в 💇 МЕСТО

✨ {service}
👤 {staff}

👉 Отправьте + для подтверждения
Или напишите, если планы изменились"""
    ]
    return random.choice(templates)


def msg_confirmed(client_name: str, dt: datetime) -> str:
    """Ответ на подтверждение записи"""
    date_str = format_date(dt)
    time_str = format_time(dt)
    
    return f"""✅ {client_name}, ваша запись подтверждена!

📅 {date_str} в {time_str}
💇 МЕСТО ждёт вас!

До встречи! 🌟"""


def msg_reminder_1h(client_name: str, service: str, staff: str, dt: datetime) -> str:
    """Напоминание за час"""
    time_str = format_time(dt)
    
    templates = [
        f"""⏳ Ждём вас через час, {client_name}!

⏰ Время: {time_str}
💇 МЕСТО
👤 {staff}

До скорой встречи! 🌟""",

        f"""⏰ {client_name}, через час ваш визит!

Мы вас ждём в {time_str} 😊

💇 {service}
👤 {staff}

До встречи! ✨"""
    ]
    return random.choice(templates)


def msg_booking_changed(client_name: str, service: str, staff: str, dt: datetime) -> str:
    """При изменении записи"""
    date_str = format_date(dt)
    time_str = format_time(dt)
    
    return f"""{client_name}, это 💇 МЕСТО

Ваша запись изменена:

📅 Новая дата: {date_str}
⏰ Новое время: {time_str}
✨ {service}
👤 {staff}

Если у вас есть вопросы — напишите нам 💬"""


def msg_booking_cancelled(client_name: str, service: str, dt: datetime) -> str:
    """При удалении записи"""
    date_str = format_date(dt)
    time_str = format_time(dt)
    
    templates = [
        f"""😔 {client_name}, ваша запись на {date_str} в {time_str} отменена.

Мы будем рады видеть вас снова в 💇 МЕСТО!

Записаться можно в любое удобное время 💬""",

        f"""{client_name}, запись отменена

📅 {date_str} в {time_str}
✨ {service}

Ждём вас снова в 💇 МЕСТО! 🌟"""
    ]
    return random.choice(templates)


def msg_review_request(client_name: str, service: str, staff: str) -> str:
    """Запрос отзыва после визита"""
    templates = [
        f"""😊 {client_name}, спасибо что выбрали 💇 МЕСТО!

Как прошёл ваш визит? Нам важно ваше мнение!

Мастер {staff} будет рад вашему отзыву ⭐

Оставьте отзыв или напишите нам, если что-то не понравилось — мы всё исправим 🙏""",

        f"""✨ {client_name}, благодарим за визит!

Надеемся, вам всё понравилось 😊

Будем признательны за отзыв о работе мастера {staff} ⭐

До новых встреч в 💇 МЕСТО!""",

        f"""😊 Спасибо, что выбрали нас, {client_name}!

Как вам результат? Мастер {staff} старался для вас ✨

Ваш отзыв поможет нам стать лучше ⭐

Ждём вас снова! 💇 МЕСТО"""
    ]
    return random.choice(templates)


def msg_lost_client_21(client_name: str) -> str:
    """Потеряшки - 21 день"""
    templates = [
        f"""👋 {client_name}, добрый день!

Это салон 💇 МЕСТО

Давно вас не видели — уже 3 недели прошло! 

Может, пора обновить образ? 💇✨

Запишитесь — мы соскучились! 😊""",

        f"""Привет, {client_name}! 👋

Это 💇 МЕСТО — мы заметили, что вы давно не заглядывали к нам

Может, самое время? 😊

Ждём вас! ✨"""
    ]
    return random.choice(templates)


def msg_lost_client_35(client_name: str) -> str:
    """Потеряшки - 35 дней"""
    templates = [
        f"""👋 {client_name}, добрый день!

Это администратор 💇 МЕСТО

Прошло больше месяца с вашего последнего визита 📅

Мы скучаем! Запишитесь — порадуем вас отличным результатом ✨""",

        f"""{client_name}, мы вас потеряли! 😢

💇 МЕСТО ждёт вас уже больше месяца

Может, пора навестить любимый салон? 

Запишитесь — будем рады! 😊"""
    ]
    return random.choice(templates)


def msg_lost_client_65(client_name: str) -> str:
    """Потеряшки - 65 дней"""
    templates = [
        f"""👋 {client_name}, добрый день!

Это администратор 💇 МЕСТО

Вас не было уже 2 месяца! Всё ли в порядке? 🤔

Мы будем очень рады видеть вас снова ✨

Запишитесь — вернём красоту! 💇""",

        f"""{client_name}, как давно мы не виделись! 😊

💇 МЕСТО скучает по вам

Прошло уже 2 месяца... Может, заглянете? ✨

Ждём! 🌟"""
    ]
    return random.choice(templates)

