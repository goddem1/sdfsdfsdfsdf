#!/usr/bin/env bash
set -euo pipefail

# Пример скрипта развёртывания бота на сервере с Ubuntu/Debian.
# Запускать под root на СЕРВЕРЕ (109.172.6.250), ПОсле того как код проекта уже скопирован в /opt/telegram-bot.
#
# Пример копирования проекта с локального компьютера:
#   scp -r ~/telegram-bot root@109.172.6.250:/opt/telegram-bot
#
# ВАЖНО: перед включением systemd‑сервиса нужно отредактировать telegram-bot.service
# и прописать настоящий BOT_TOKEN от BotFather.

PROJECT_DIR="/opt/telegram-bot"
PYTHON_BIN="python3"

echo "==> Устанавливаю зависимости системы..."
apt update
apt install -y python3 python3-venv python3-pip

echo "==> Перехожу в каталог проекта: ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

echo "==> Создаю и активирую виртуальное окружение..."
${PYTHON_BIN} -m venv .venv
source .venv/bin/activate

echo "==> Обновляю pip и ставлю зависимости..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Проверяю тестовый запуск бота (Ctrl+C для остановки)..."
echo "    Перед запуском укажите переменную BOT_TOKEN в этой сессии:"
echo "    export BOT_TOKEN='ТОКЕН_ОТ_BOTFATHER'"
echo
read -r -p "Продолжить тестовый запуск? [y/N] " ans
if [[ "${ans:-N}" =~ ^[Yy]$ ]]; then
  python3 bot_ui.py
fi

echo
echo "==> Скрипт закончил работу."
echo "Дальше скопируйте файл telegram-bot.service.example в /etc/systemd/system/telegram-bot.service,"
echo "подставьте туда ваш BOT_TOKEN и выполните:"
echo "  systemctl daemon-reload"
echo "  systemctl enable --now telegram-bot"
echo "  systemctl status telegram-bot"

