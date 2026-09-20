use std::env;
use std::process;

// Полный алфавит: 93 символа (A-Z, a-z, 1-9, 32 спецсимвола ASCII), ~6,54 бита на символ
const FULL: &[u8] =
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~";

// Для URL и имён файлов: 64 символа, 6 бит на символ
const SAFE: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

const DEFAULT_BITS: u32 = 128;
const BITS_ERR: &str = "bits: от 128 до 256";

const USAGE: &str = "Использование: rid [bits] [--safe]\n  bits    стойкость, 128-256 (по умолчанию 128)\n  --safe  алфавит из 64 символов без спецсимволов (URL, имена файлов)";

#[derive(Debug, PartialEq)]
enum Parsed {
    Help,
    Run { bits: u32, safe: bool },
}

/// Строгий разбор аргументов. Те же правила в python/rid.py:
/// не более одного числа, не более одного --safe, любой другой аргумент это ошибка.
/// Число только из ASCII-цифр (без знака, пробелов и подчёркиваний).
fn parse_args(args: &[String]) -> Result<Parsed, String> {
    let mut bits: Option<u32> = None;
    let mut safe = false;

    for a in args {
        match a.as_str() {
            "-h" | "--help" => return Ok(Parsed::Help),
            "--safe" => {
                if safe {
                    return Err("--safe указан дважды".to_string());
                }
                safe = true;
            }
            s if !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit()) => {
                if bits.is_some() {
                    return Err("bits указан дважды".to_string());
                }
                bits = Some(s.parse().map_err(|_| BITS_ERR.to_string())?);
            }
            s => return Err(format!("неизвестный аргумент: {}", s)),
        }
    }

    let bits = bits.unwrap_or(DEFAULT_BITS);
    if !(128..=256).contains(&bits) {
        return Err(BITS_ERR.to_string());
    }
    Ok(Parsed::Run { bits, safe })
}

/// Длина строки, при которой энтропия не меньше `bits`.
fn length_for(alphabet: &[u8], bits: u32) -> usize {
    (bits as f64 / (alphabet.len() as f64).log2()).ceil() as usize
}

/// Случайная строка длиной `len`. Байты >= limit отбрасываются,
/// чтобы остаток от деления не давал перекос в сторону первых символов.
fn random_string(alphabet: &[u8], len: usize) -> String {
    let n = alphabet.len();
    let limit = 256 / n * n; // для 93 это 186, для 64 это 256

    let mut out = String::with_capacity(len);
    let mut buf = [0u8; 64];
    while out.len() < len {
        getrandom::getrandom(&mut buf).expect("ОС не отдала случайные байты");
        for &b in &buf {
            if (b as usize) < limit && out.len() < len {
                out.push(alphabet[b as usize % n] as char);
            }
        }
    }
    out
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    match parse_args(&args) {
        Err(e) => {
            eprintln!("{}", e);
            eprintln!("{}", USAGE);
            process::exit(2);
        }
        Ok(Parsed::Help) => println!("{}", USAGE),
        Ok(Parsed::Run { bits, safe }) => {
            let alphabet = if safe { SAFE } else { FULL };
            let s = random_string(alphabet, length_for(alphabet, bits));
            println!("{}", s);
            eprintln!("{} бит, {} символов", bits, s.len());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(a: &[&str]) -> Vec<String> {
        a.iter().map(|s| s.to_string()).collect()
    }

    fn run(bits: u32, safe: bool) -> Result<Parsed, String> {
        Ok(Parsed::Run { bits, safe })
    }

    #[test]
    fn lengths_full() {
        assert_eq!(length_for(FULL, 128), 20);
        assert_eq!(length_for(FULL, 192), 30);
        assert_eq!(length_for(FULL, 256), 40);
    }

    #[test]
    fn lengths_safe() {
        assert_eq!(length_for(SAFE, 128), 22);
        assert_eq!(length_for(SAFE, 192), 32);
        assert_eq!(length_for(SAFE, 256), 43);
    }

    #[test]
    fn only_alphabet_chars() {
        for alphabet in [FULL, SAFE] {
            let s = random_string(alphabet, 1000);
            assert_eq!(s.len(), 1000);
            assert!(s.bytes().all(|b| alphabet.contains(&b)));
        }
    }

    #[test]
    fn full_has_no_zero() {
        assert!(!random_string(FULL, 5000).contains('0'));
    }

    #[test]
    fn args_valid() {
        assert_eq!(parse_args(&v(&[])), run(128, false));
        assert_eq!(parse_args(&v(&["192"])), run(192, false));
        assert_eq!(parse_args(&v(&["256", "--safe"])), run(256, true));
        assert_eq!(parse_args(&v(&["--safe", "192"])), run(192, true));
        assert_eq!(parse_args(&v(&["--safe"])), run(128, true));
        assert_eq!(parse_args(&v(&["--help"])), Ok(Parsed::Help));
        assert_eq!(parse_args(&v(&["-h"])), Ok(Parsed::Help));
    }

    #[test]
    fn args_invalid() {
        for bad in [
            &["128", "--unknown"][..],
            &["128", "256"],
            &["--safe", "--safe"],
            &["127"],
            &["257"],
            &["+128"],
            &["-5"],
            &["1_28"],
            &["99999999999999999999"],
            &["abc"],
            &[""],
        ] {
            assert!(parse_args(&v(bad)).is_err(), "должно быть ошибкой: {:?}", bad);
        }
    }
}
