#!/usr/bin/env python3
# BSD 3-Clause License. Skhoron-SrcBox.
# Перехват пакетов через AF_PACKET (Linux, root, без зависимостей).
# Пишет .pcap, который открывается в Wireshark.
#
# Примеры:
#   sudo python3 sniff.py
#   sudo python3 sniff.py -i wlan0 --proto tcp --port 443
#   sudo python3 sniff.py --host 1.1.1.1 -c 100 -w dump.pcap

import argparse
import socket
import struct
import sys
import time

ETH_P_ALL = 0x0003
TCP_FLAGS = [(0x20, "URG"), (0x10, "ACK"), (0x08, "PSH"), (0x04, "RST"), (0x02, "SYN"), (0x01, "FIN")]


def mac(b):
    return ":".join(f"{x:02x}" for x in b)


def dns_name(data, off):
    parts = []
    while off < len(data):
        n = data[off]
        if n == 0 or n & 0xC0:
            break
        parts.append(data[off + 1:off + 1 + n].decode("ascii", "replace"))
        off += n + 1
    return ".".join(parts)


def parse(frame):
    if len(frame) < 14:
        return None
    dst, src, etype = struct.unpack("!6s6sH", frame[:14])
    off = 14
    if etype == 0x8100 and len(frame) >= 18:
        etype = struct.unpack("!H", frame[16:18])[0]
        off = 18
    p = {"proto": "eth", "src": mac(src), "dst": mac(dst), "sport": None, "dport": None, "info": ""}

    if etype == 0x0806 and len(frame) >= off + 28:
        op = struct.unpack("!H", frame[off + 6:off + 8])[0]
        p["proto"] = "arp"
        p["src"] = socket.inet_ntoa(frame[off + 14:off + 18])
        p["dst"] = socket.inet_ntoa(frame[off + 24:off + 28])
        p["info"] = "who-has" if op == 1 else "is-at"
        return p

    if etype == 0x0800 and len(frame) >= off + 20:
        ihl = (frame[off] & 0x0F) * 4
        proto = frame[off + 9]
        p["src"] = socket.inet_ntoa(frame[off + 12:off + 16])
        p["dst"] = socket.inet_ntoa(frame[off + 16:off + 20])
        l4 = off + ihl
    elif etype == 0x86DD and len(frame) >= off + 40:
        proto = frame[off + 6]  # расширенные заголовки IPv6 не разбираются
        p["src"] = socket.inet_ntop(socket.AF_INET6, frame[off + 8:off + 24])
        p["dst"] = socket.inet_ntop(socket.AF_INET6, frame[off + 24:off + 40])
        l4 = off + 40
    else:
        p["proto"] = f"0x{etype:04x}"
        return p

    if proto == 6 and len(frame) >= l4 + 14:
        sp, dp, seq, ack, of = struct.unpack("!HHLLH", frame[l4:l4 + 14])
        p.update(proto="tcp", sport=sp, dport=dp)
        fl = [n for bit, n in TCP_FLAGS if of & bit]
        p["info"] = "[" + ",".join(fl) + "] len=" + str(len(frame) - l4 - ((of >> 12) * 4))
    elif proto == 17 and len(frame) >= l4 + 8:
        sp, dp, ln, _ = struct.unpack("!HHHH", frame[l4:l4 + 8])
        p.update(proto="udp", sport=sp, dport=dp)
        p["info"] = f"len={ln - 8}"
        if 53 in (sp, dp) and len(frame) >= l4 + 8 + 13:
            p["proto"] = "dns"
            p["info"] = ("resp " if frame[l4 + 10] & 0x80 else "query ") + dns_name(frame, l4 + 8 + 12)
    elif proto in (1, 58) and len(frame) >= l4 + 2:
        p["proto"] = "icmp" if proto == 1 else "icmp6"
        p["info"] = f"type={frame[l4]} code={frame[l4 + 1]}"
    else:
        p["proto"] = f"ip/{proto}"
    return p


def match(p, a):
    if a.proto:
        base = "udp" if p["proto"] == "dns" else p["proto"]
        if a.proto not in (p["proto"], base):
            return False
    if a.port and a.port not in (p["sport"], p["dport"]):
        return False
    if a.host and a.host not in (p["src"], p["dst"]):
        return False
    return True


def pcap_header():
    return struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)


def main():
    ap = argparse.ArgumentParser(description="Перехват пакетов (AF_PACKET)")
    ap.add_argument("-i", "--iface", help="интерфейс (по умолчанию все)")
    ap.add_argument("--proto", choices=["tcp", "udp", "dns", "icmp", "icmp6", "arp"])
    ap.add_argument("--port", type=int)
    ap.add_argument("--host", help="IP отправителя или получателя")
    ap.add_argument("-c", "--count", type=int, default=0, help="остановиться после N пакетов")
    ap.add_argument("-w", "--write", help="сохранить в .pcap")
    a = ap.parse_args()

    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(ETH_P_ALL))
    except PermissionError:
        sys.exit("Нужен root: sudo python3 sniff.py")
    if a.iface:
        s.bind((a.iface, 0))

    out = open(a.write, "wb") if a.write else None
    if out:
        out.write(pcap_header())

    n = 0
    t0 = time.time()
    try:
        while not a.count or n < a.count:
            frame, _ = s.recvfrom(65535)
            p = parse(frame)
            if not p or not match(p, a):
                continue
            now = time.time()
            n += 1
            if out:
                out.write(struct.pack("<IIII", int(now), int((now % 1) * 1e6), len(frame), len(frame)) + frame)
            src = p["src"] + (f":{p['sport']}" if p["sport"] is not None else "")
            dst = p["dst"] + (f":{p['dport']}" if p["dport"] is not None else "")
            print(f"{now - t0:9.4f} {p['proto']:<6} {src:<42} > {dst:<42} {p['info']}")
    except KeyboardInterrupt:
        pass
    finally:
        if out:
            out.close()
        print(f"\nпакетов: {n}", file=sys.stderr)


if __name__ == "__main__":
    main()