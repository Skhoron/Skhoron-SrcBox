#!/usr/bin/env python3
# BSD 3-Clause License. Skhoron-SrcBox.
# Активные сетевые соединения с именем процесса.
# Зависимость: pip install psutil. Для чужих процессов нужен root.
# Запуск: sudo python3 netconns.py [-w] [--listen]
#   -w        обновлять каждые 2 секунды
#   --listen  показывать только слушающие порты

import sys
import time

import psutil


def addr(a):
    return f"{a.ip}:{a.port}" if a else "-"


def snapshot(listen_only):
    rows = []
    for c in psutil.net_connections(kind="inet"):
        if listen_only and c.status != psutil.CONN_LISTEN:
            continue
        name = "-"
        if c.pid:
            try:
                name = psutil.Process(c.pid).name()
            except psutil.NoSuchProcess:
                pass
        proto = "tcp" if c.type == 1 else "udp"
        rows.append((proto, addr(c.laddr), addr(c.raddr), c.status, c.pid or 0, name))
    return sorted(rows, key=lambda r: (r[3], r[5]))


def show(rows):
    print(f"{'PROTO':<6}{'LOCAL':<26}{'REMOTE':<26}{'STATE':<13}{'PID':<8}PROC")
    for r in rows:
        print(f"{r[0]:<6}{r[1]:<26}{r[2]:<26}{r[3]:<13}{r[4]:<8}{r[5]}")


def main():
    watch = "-w" in sys.argv
    listen_only = "--listen" in sys.argv
    try:
        while True:
            if watch:
                print("\033[2J\033[H", end="")
            show(snapshot(listen_only))
            if not watch:
                break
            time.sleep(2)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()