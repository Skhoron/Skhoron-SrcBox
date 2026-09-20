#!/usr/bin/env python3
"""Короткий случайный ID со стойкостью 128-256 бит.

Использование: rid.py [bits] [--safe]
"""
import math
import secrets
import string
import sys

FULL = string.ascii_letters + "123456789" + string.punctuation  # 93 символа
SAFE = string.ascii_letters + string.digits + "-_"  # 64 символа, для URL и имён файлов

DEFAULT_BITS = 128
BITS_ERR = "bits: от 128 до 256"

USAGE = (
    "Использование: rid [bits] [--safe]\n"
    "  bits    стойкость, 128-256 (по умолчанию 128)\n"
    "  --safe  алфавит из 64 символов без спецсимволов (URL, имена файлов)"
)


class ArgError(Exception):
    pass


def parse_args(args):
    """Строгий разбор аргументов. Те же правила в src/main.rs:
    не более одного числа, не более одного --safe, любой другой аргумент это ошибка.
    Число только из ASCII-цифр (без знака, пробелов и подчёркиваний).

    Возвращает None для --help, иначе (bits, safe).
    """
    bits = None
    safe = False
    for a in args:
        if a in ("-h", "--help"):
            return None
        if a == "--safe":
            if safe:
                raise ArgError("--safe указан дважды")
            safe = True
        elif a.isascii() and a.isdigit():
            if bits is not None:
                raise ArgError("bits указан дважды")
            try:
                bits = int(a)
            except ValueError:  # слишком длинное число
                raise ArgError(BITS_ERR)
        else:
            raise ArgError(f"неизвестный аргумент: {a}")

    if bits is None:
        bits = DEFAULT_BITS
    if not 128 <= bits <= 256:
        raise ArgError(BITS_ERR)
    return bits, safe


def length_for(alphabet: str, bits: int) -> int:
    return math.ceil(bits / math.log2(len(alphabet)))


def gen(bits: int = DEFAULT_BITS, safe: bool = False) -> str:
    if not 128 <= bits <= 256:
        raise ValueError(BITS_ERR)
    alphabet = SAFE if safe else FULL
    return "".join(secrets.choice(alphabet) for _ in range(length_for(alphabet, bits)))


def main() -> None:
    try:
        parsed = parse_args(sys.argv[1:])
    except ArgError as e:
        print(e, file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(2)

    if parsed is None:
        print(USAGE)
        return

    bits, safe = parsed
    s = gen(bits, safe)
    print(s)
    print(f"{bits} бит, {len(s)} символов", file=sys.stderr)


if __name__ == "__main__":
    main()