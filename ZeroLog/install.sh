#!/bin/bash
# Обёртка для удалённого запуска ZeroLog без клонирования репозитория.
#
#   curl -fsSL https://raw.githubusercontent.com/Skhoron/Skhoron-SrcBox/main/ZeroLog/install.sh | sudo bash
#
# Скачивает zerolog.sh во временный файл и запускает его в режиме apply.

set -e

RAW_URL="https://raw.githubusercontent.com/Skhoron/Skhoron-SrcBox/main/ZeroLog/zerolog.sh"
TMP_FILE="$(mktemp /tmp/zerolog.XXXXXX.sh)"

cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

echo "[*] Скачивание zerolog.sh..."
curl -fsSL "$RAW_URL" -o "$TMP_FILE"
chmod +x "$TMP_FILE"

echo "[*] Запуск..."
bash "$TMP_FILE" "$@"