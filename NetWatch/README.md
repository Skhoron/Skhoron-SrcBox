# NetWatch

Три небольших скрипта для просмотра сетевой активности в Linux. Часть Skhoron-SrcBox, лицензия BSD-3.

Скрипты ничего не имитируют: `sniff.py` читает реальные пакеты с интерфейса, `speed.py` берёт счётчики ядра из `/proc/net/dev`, `conns.py` берёт таблицу соединений через `psutil`.

## Файлы

| Файл | Что делает | Зависимости |
|---|---|---|
| `sniff.py` | Перехват пакетов в духе Wireshark/tcpdump: TCP, UDP, DNS, ICMP, ARP, IPv4/IPv6. Пишет `.pcap` | нет |
| `speed.py` | Скорость RX/TX по интерфейсам | нет |
| `conns.py` | Открытые соединения и слушающие порты с именем процесса | `psutil` |

## Запуск

```
sudo python3 sniff.py
sudo python3 sniff.py -i wlan0 --proto tcp --port 443
sudo python3 sniff.py --proto dns
sudo python3 sniff.py --host 1.1.1.1 -c 100 -w dump.pcap

python3 speed.py 2

pip install -r requirements.txt
sudo python3 conns.py -w
sudo python3 conns.py --listen
```

Файл `dump.pcap` открывается в Wireshark как есть.

## Ограничения

- Только Linux (`AF_PACKET`).
- `sniff.py` требует root или `CAP_NET_RAW`.
- Расширенные заголовки IPv6 не разбираются: пакеты с ними будут показаны как `ip/<номер>`.
- Содержимое TLS не расшифровывается, виден только заголовок и размер.
- Фильтры простые: один протокол, один порт, один хост. Выражения BPF не поддерживаются.
- Перехватывать трафик можно только в своих сетях и на своих устройствах.