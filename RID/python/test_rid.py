import subprocess
import sys
import unittest
from pathlib import Path

import rid

SCRIPT = str(Path(__file__).with_name("rid.py"))


def cli(*args):
    return subprocess.run(
        [sys.executable, SCRIPT, *args], capture_output=True, text=True
    )


class Lengths(unittest.TestCase):
    def test_full(self):
        self.assertEqual(
            [len(rid.gen(b)) for b in (128, 192, 256)], [20, 30, 40]
        )

    def test_safe(self):
        self.assertEqual(
            [len(rid.gen(b, safe=True)) for b in (128, 192, 256)], [22, 32, 43]
        )

    def test_default_is_128(self):
        self.assertEqual(len(rid.gen()), 20)


class Alphabet(unittest.TestCase):
    def test_full_chars_and_no_zero(self):
        s = "".join(rid.gen(256) for _ in range(200))
        self.assertTrue(set(s) <= set(rid.FULL))
        self.assertNotIn("0", s)

    def test_safe_chars(self):
        s = "".join(rid.gen(256, safe=True) for _ in range(200))
        self.assertTrue(set(s) <= set(rid.SAFE))

    def test_sizes(self):
        self.assertEqual(len(rid.FULL), 93)
        self.assertEqual(len(rid.SAFE), 64)


class ParseArgs(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(rid.parse_args([]), (128, False))
        self.assertEqual(rid.parse_args(["192"]), (192, False))
        self.assertEqual(rid.parse_args(["256", "--safe"]), (256, True))
        self.assertEqual(rid.parse_args(["--safe", "192"]), (192, True))
        self.assertEqual(rid.parse_args(["--safe"]), (128, True))
        self.assertIsNone(rid.parse_args(["--help"]))
        self.assertIsNone(rid.parse_args(["-h"]))

    def test_invalid(self):
        for bad in (
            ["128", "--unknown"],
            ["128", "256"],
            ["--safe", "--safe"],
            ["127"],
            ["257"],
            ["+128"],
            ["-5"],
            ["1_28"],
            [" 128"],
            ["١٢٨"],  # арабо-индийские цифры
            ["9" * 5000],
            ["abc"],
            [""],
        ):
            with self.subTest(args=bad):
                with self.assertRaises(rid.ArgError):
                    rid.parse_args(bad)


class Cli(unittest.TestCase):
    def test_ok_stdout_only_id(self):
        r = cli("128")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(len(r.stdout.strip()), 20)
        self.assertEqual(r.stderr.strip(), "128 бит, 20 символов")

    def test_safe_192(self):
        r = cli("192", "--safe")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(len(r.stdout.strip()), 32)

    def test_errors_exit_2_and_empty_stdout(self):
        for args in (["128", "--unknown"], ["128", "256"], ["100"], ["abc"]):
            with self.subTest(args=args):
                r = cli(*args)
                self.assertEqual(r.returncode, 2)
                self.assertEqual(r.stdout, "")

    def test_help(self):
        r = cli("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Использование: rid", r.stdout)


if __name__ == "__main__":
    unittest.main()