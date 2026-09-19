#!/usr/bin/env python3
# BSD 3-Clause License. Skhoron-SrcBox.
# Скорость приёма/передачи по интерфейсам (Linux, без зависимостей).
# Запуск: python3 netspeed.py [интервал_сек]

import sys
import time


def read_counters():
    data = {}
    with open("/proc/net/dev") as f:
        for line in f.readlines()[2:]:
            name, stats = line.split(":", 1)
            cols = stats.split()
            data[name.strip()] = (int(cols[0]), int(cols[8]))  # rx_bytes, tx_bytes
    return data


def fmt(n):
    for unit in ("Б/с", "КБ/с", "МБ/с", "ГБ/с"):
        if n < 1024:
            return f"{n:7.1f} {unit}"
        n /= 1024
    return f"{n:7.1f} ТБ/с"


def main():
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    prev = read_counters()
    try:
        while True:
            time.sleep(interval)
            cur = read_counters()
            print("\033[2J\033[H", end="")
            print(f"{'iface':<12}{'RX':>14}{'TX':>14}")
            for name, (rx, tx) in cur.items():
                if name not in prev:
                    continue
                drx = (rx - prev[name][0]) / interval
                dtx = (tx - prev[name][1]) / interval
                print(f"{name:<12}{fmt(drx):>14}{fmt(dtx):>14}")
            prev = cur
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()