#!/data/data/com.termux/files/usr/bin/bash

echo "🚀 Запуск казино-бота..."
echo "📅 Дата: $(date)"

# Установите минимальные зависимости
export PIP_NO_BUILD_ISOLATION=1
export CARGO_BUILD_TARGET=aarch64-linux-android

# Проверяем Python
python3 --version

# Проверяем установленные пакеты
echo "📦 Установленные пакеты:"
pip list | grep -E "aiogram|aiohttp|aiocryptopay|apscheduler|pytz" || true

# Запускаем бота
echo "▶️ Запуск main.py..."
cd "$(dirname "$0")"
python3 main.py