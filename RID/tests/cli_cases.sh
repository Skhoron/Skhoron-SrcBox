#!/bin/sh
# Запускает Rust- и Python-версии на одних и тех же аргументах и сравнивает
# код возврата, stderr и длину stdout. Запуск из любого места: sh RID/tests/cli_cases.sh
set -u
cd "$(dirname "$0")/.." || exit 1
cargo build --release -q || exit 1

BIN=target/release/rid
fail=0

while IFS= read -r line; do
    # shellcheck disable=SC2086
    set -- $line

    r_err=$($BIN "$@" 2>&1 >/dev/null); r_code=$?
    p_err=$(python3 python/rid.py "$@" 2>&1 >/dev/null); p_code=$?
    r_len=$($BIN "$@" 2>/dev/null | wc -c)
    p_len=$(python3 python/rid.py "$@" 2>/dev/null | wc -c)

    if [ "$r_code" != "$p_code" ] || [ "$r_err" != "$p_err" ] || [ "$r_len" != "$p_len" ]; then
        echo "РАЗНИЦА для [$line]: rust code=$r_code len=$r_len err='$r_err' | python code=$p_code len=$p_len err='$p_err'"
        fail=1
    fi
done << 'CASES'

128
192
256
128 --safe
--safe 256
--safe
--help
-h
128 --unknown
128 256
--safe --safe
127
257
+128
-5
1_28
abc
99999999999999999999
CASES

[ "$fail" = 0 ] && echo "Rust и Python совпали на всех случаях"
exit "$fail"