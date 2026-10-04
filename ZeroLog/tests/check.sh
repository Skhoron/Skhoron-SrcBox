#!/bin/bash
# Простой CI-тест: применяет zerolog.sh и проверяет, что --check
# после этого возвращает успех (exit 0).
#
# Предполагается запуск в одноразовом контейнере/VM с systemd,
# НЕ на реальном продакшен-сервере.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZEROLOG="$SCRIPT_DIR/../zerolog.sh"

echo "== ZeroLog CI test =="

echo "[*] Запуск apply..."
bash "$ZEROLOG"

echo "[*] Запуск --check..."
if bash "$ZEROLOG" --check; then
  echo "[PASS] Нода соответствует ZeroLog-политике после apply"
  exit 0
else
  echo "[FAIL] Нода НЕ соответствует политике после apply — регрессия"
  exit 1
fi