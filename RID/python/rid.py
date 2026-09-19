#!/usr/bin/env python3
"""Короткий случайный ID со стойкостью 128-256 бит.

Использование: rid.py [bits] [--safe]
"""
import math
import secrets
import string
import sys

FULL = string.ascii_letters + "123456789" + string.punctuation  # 93 символа
SAFE = string.ascii_letters + string.digits + "-_"  # 64 символа, годится для URL

DEFAULT_BITS = 128


def length_for(alphabet: str, bits: int) -> int:
    return math.ceil(bits / math.log2(len(alphabet)))


def gen(bits: int = DEFAULT_BITS, safe: bool = False) -> str:
    if not 128 <= bits <= 256:
        raise ValueError("bits: от 128 до 256")
    alphabet = SAFE if safe else FULL
    return "".join(secrets.choice(alphabet) for _ in range(length_for(alphabet, bits)))


def main() -> None:
    args = sys.argv[1:]
    safe = "--safe" in args
    rest = [a for a in args if a != "--safe"]
    try:
        bits = int(rest[0]) if rest else DEFAULT_BITS
        s = gen(bits, safe)
    except ValueError as e:
        sys.exit(str(e))
    print(s)
    print(f"{bits} бит, {len(s)} символов", file=sys.stderr)


if __name__ == "__main__":
    main()