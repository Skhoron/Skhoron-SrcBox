# ZeroLog

Часть экосистемы Skhoron: `Skhoron/Skhoron-SrcBox/ZeroLog`

Скрипт для нод P2P-сети (например, P2P), гарантирующий, что сервер
не хранит логи на диске: journald переводится в volatile-режим,
rsyslog/syslog-ng/auditd отключаются, `/var/log` монтируется как tmpfs,
swap выключается, история шелла и auth-логи (lastlog/wtmp/btmp) ведут
в `/dev/null`.

## Использование

```bash
sudo bash zerolog.sh           # применить настройки
sudo bash zerolog.sh --check   # только проверить текущее состояние (без изменений)
bash zerolog.sh --report       # вывести JSON-отчёт (root не обязателен)
```

Либо через обёртку:

```bash
curl -fsSL https://raw.githubusercontent.com/Skhoron/Skhoron-SrcBox/main/ZeroLog/install.sh | sudo bash
```

## Что проверяется

| Параметр | Что означает |
|---|---|
| `journald_volatile` | journald хранит логи только в RAM |
| `rsyslog_disabled` | rsyslog/syslog-ng выключены |
| `varlog_tmpfs` | `/var/log` смонтирован как tmpfs |
| `swap_disabled` | swap выключен (RAM-данные не утекают на диск) |
| `shell_history_disabled` | история bash/zsh ведёт в `/dev/null` |
| `auditd_disabled` | auditd выключен |

## Честные ограничения

Это конфигурация ОС, а не криптографическая аттестация. JSON-отчёт
из `--report` можно подделать на уровне самого оператора ноды —
для реальной верифицируемой гарантии нужен отдельный протокол доверия
(подпись отчёта, аттестация на уровне STP-хендшейка). См. `docs/PROTOCOL.md`.

## Лицензия

BSD-3 (см. `LICENSE`), как и весь репозиторий Skhoron-SrcBox.