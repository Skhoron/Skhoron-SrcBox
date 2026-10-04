#!/bin/bash
# ZeroLog — скрипт для нод P2P-сети: гарантирует, что сервер не хранит
# логи на диске (journald, rsyslog, auditd, shell history, auth-логи и т.д.)
#
# Часть: Skhoron/Skhoron-SrcBox/ZeroLog
#
# Использование:
#   sudo bash zerolog.sh           # применить настройки
#   sudo bash zerolog.sh --check   # только проверить текущее состояние
#   bash zerolog.sh --report       # вывести JSON-отчёт (root не обязателен)

set -e
shopt -s nullglob

MODE="${1:-apply}"

need_root() {
  if [ "$EUID" -ne 0 ]; then
    echo "Нужны права root (sudo)." >&2
    exit 1
  fi
}

# ---------- ПРОВЕРКА ТЕКУЩЕГО СОСТОЯНИЯ ----------
check_status() {
  local ok=1

  echo "== ZeroLog: проверка состояния =="

  if grep -rq "Storage=volatile" /etc/systemd/journald.conf.d/ 2>/dev/null; then
    echo "[OK]   journald: volatile (RAM only)"
  else
    echo "[FAIL] journald: персистентное хранилище"
    ok=0
  fi

  if ! systemctl is-active --quiet rsyslog 2>/dev/null; then
    echo "[OK]   rsyslog: выключен"
  else
    echo "[FAIL] rsyslog: активен"
    ok=0
  fi

  if mount | grep -q "on /var/log type tmpfs"; then
    echo "[OK]   /var/log: tmpfs (RAM, не диск)"
  else
    echo "[FAIL] /var/log: на постоянном хранилище"
    ok=0
  fi

  if [ -z "$(swapon --show 2>/dev/null)" ]; then
    echo "[OK]   swap: выключен"
  else
    echo "[FAIL] swap: активен (данные могут утечь на диск)"
    ok=0
  fi

  if [ "$(readlink -f /root/.bash_history 2>/dev/null)" = "/dev/null" ]; then
    echo "[OK]   bash_history: /dev/null"
  else
    echo "[FAIL] bash_history: пишется на диск"
    ok=0
  fi

  if ! systemctl is-active --quiet auditd 2>/dev/null; then
    echo "[OK]   auditd: выключен"
  else
    echo "[FAIL] auditd: активен"
    ok=0
  fi

  echo
  if [ "$ok" -eq 1 ]; then
    echo "РЕЗУЛЬТАТ: нода соответствует ZeroLog-политике"
    return 0
  else
    echo "РЕЗУЛЬТАТ: нода НЕ соответствует, нужно запустить без --check"
    return 1
  fi
}

# ---------- JSON-ОТЧЁТ ДЛЯ ВЕРИФИКАЦИИ ПИРАМИ ----------
report_json() {
  local journald_ok rsyslog_ok tmpfs_ok swap_ok hist_ok audit_ok ts host

  grep -rq "Storage=volatile" /etc/systemd/journald.conf.d/ 2>/dev/null && journald_ok=true || journald_ok=false
  systemctl is-active --quiet rsyslog 2>/dev/null && rsyslog_ok=false || rsyslog_ok=true
  mount | grep -q "on /var/log type tmpfs" && tmpfs_ok=true || tmpfs_ok=false
  [ -z "$(swapon --show 2>/dev/null)" ] && swap_ok=true || swap_ok=false
  [ "$(readlink -f /root/.bash_history 2>/dev/null)" = "/dev/null" ] && hist_ok=true || hist_ok=false
  systemctl is-active --quiet auditd 2>/dev/null && audit_ok=false || audit_ok=true

  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  host=$(hostname 2>/dev/null || echo "unknown")

  cat <<EOF
{
  "node_host": "$host",
  "checked_at": "$ts",
  "journald_volatile": $journald_ok,
  "rsyslog_disabled": $rsyslog_ok,
  "varlog_tmpfs": $tmpfs_ok,
  "swap_disabled": $swap_ok,
  "shell_history_disabled": $hist_ok,
  "auditd_disabled": $audit_ok
}
EOF
}

# ---------- ПРИМЕНЕНИЕ НАСТРОЕК ----------
apply_settings() {
  need_root

  echo "[1/9] journald -> только RAM, авто-очистка"
  mkdir -p /etc/systemd/journald.conf.d
  cat > /etc/systemd/journald.conf.d/no-persist.conf <<'EOF'
[Journal]
Storage=volatile
RuntimeMaxUse=8M
RuntimeMaxFileSize=4M
MaxRetentionSec=1min
ForwardToSyslog=no
ForwardToKMsg=no
ForwardToConsole=no
ForwardToWall=no
EOF
  rm -rf /var/log/journal
  systemctl restart systemd-journald

  echo "[2/9] rsyslog/syslog-ng -> выключить и замаскировать"
  systemctl disable --now rsyslog 2>/dev/null || true
  systemctl mask rsyslog 2>/dev/null || true
  systemctl disable --now syslog-ng 2>/dev/null || true
  systemctl mask syslog-ng 2>/dev/null || true

  echo "[3/9] auditd -> выключить"
  systemctl disable --now auditd 2>/dev/null || true
  systemctl mask auditd 2>/dev/null || true

  echo "[4/9] /var/log -> tmpfs (живёт только в RAM)"
  mkdir -p /var/log
  if ! grep -q "^tmpfs /var/log" /etc/fstab; then
    echo "tmpfs /var/log tmpfs defaults,noatime,nosuid,nodev,noexec,size=32M,mode=0755 0 0" >> /etc/fstab
  fi
  mount -a 2>/dev/null || mount -o remount /var/log 2>/dev/null || true

  echo "[5/9] swap -> выключить (чтобы RAM-данные не утекали на диск)"
  swapoff -a 2>/dev/null || true
  sed -i '/\bswap\b/d' /etc/fstab

  echo "[6/9] SSH -> минимум логов"
  for cfg in /etc/ssh/sshd_config; do
    [ -f "$cfg" ] && sed -i 's/^#\?LogLevel.*/LogLevel QUIET/' "$cfg"
  done
  systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

  echo "[7/9] nginx/apache (если есть) -> логи в /dev/null"
  if command -v nginx >/dev/null 2>&1; then
    if ! grep -q "access_log off" /etc/nginx/nginx.conf 2>/dev/null; then
      sed -i "/http {/a\\
    access_log off;\\
    error_log /dev/null crit;" /etc/nginx/nginx.conf
    fi
    nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null || true
  fi
  if command -v apache2ctl >/dev/null 2>&1; then
    sed -i 's|CustomLog.*|CustomLog /dev/null combined|' /etc/apache2/apache2.conf 2>/dev/null || true
    sed -i 's|ErrorLog.*|ErrorLog /dev/null|' /etc/apache2/apache2.conf 2>/dev/null || true
  fi

  echo "[8/9] История шелла -> отключить навсегда"
  cat > /etc/profile.d/no-history.sh <<'EOF'
unset HISTFILE
export HISTSIZE=0
export HISTFILESIZE=0
EOF
  chmod +x /etc/profile.d/no-history.sh
  for f in /root/.bash_history /root/.zsh_history /home/*/.bash_history /home/*/.zsh_history; do
    rm -f "$f" 2>/dev/null || true
    ln -sf /dev/null "$f" 2>/dev/null || true
  done

  echo "[9/9] auth-логи -> /dev/null"
  for f in /var/log/lastlog /var/log/wtmp /var/log/btmp /var/run/utmp; do
    rm -f "$f" 2>/dev/null || true
    ln -sf /dev/null "$f" 2>/dev/null || true
  done

  echo
  echo "[+] ZeroLog применён: логи не пишутся на диск, остаются только в RAM до рестарта."
  echo "    Запусти с --report, чтобы получить JSON для подтверждения сети."
}

case "$MODE" in
  --check) check_status ;;
  --report) report_json ;;
  *) apply_settings && check_status ;;
esac