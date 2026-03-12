# Telegram Bot (Risk Calculator) — Starter

Минимальный каркас Telegram-бота на Python с разделением на:

- `logic.py` — бизнес-логика/формулы (без Telegram API)
- `bot_ui.py` — интерфейс бота (кнопки, команды, обработчики)

## Требования

- Python 3.11+ (можно 3.10)

## Установка

```bash
cd telegram-bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка токена

Создайте переменную окружения `BOT_TOKEN`.

```bash
export BOT_TOKEN="123456:ABCDEF_replace_with_your_token"
python bot_ui.py
```

Важно: не храните токен в репозитории. Если токен уже засветился, отзовите его в BotFather и выпустите новый.

