use std::env;
use std::process;

// Полный алфавит: 93 символа (A-Z, a-z, 1-9, 32 спецсимвола ASCII), ~6,54 бита на символ
const FULL: &[u8] =
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~";

// Безопасный для URL и файлов: 64 символа, 6 бит на символ
const SAFE: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

const DEFAULT_BITS: u32 = 128;

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

fn usage() -> ! {
    eprintln!("Использование: rid [bits] [--safe]");
    eprintln!("  bits    стойкость, 128-256 (по умолчанию {})", DEFAULT_BITS);
    eprintln!("  --safe  алфавит из 64 символов без спецсимволов (URL, имена файлов)");
    process::exit(2);
}

fn main() {
    let mut bits = DEFAULT_BITS;
    let mut safe = false;

    for arg in env::args().skip(1) {
        match arg.as_str() {
            "--safe" => safe = true,
            "-h" | "--help" => usage(),
            s => bits = s.parse().unwrap_or_else(|_| usage()),
        }
    }
    if !(128..=256).contains(&bits) {
        eprintln!("bits: от 128 до 256");
        process::exit(2);
    }

    let alphabet = if safe { SAFE } else { FULL };
    let s = random_string(alphabet, length_for(alphabet, bits));
    println!("{}", s);
    eprintln!("{} бит, {} символов", bits, s.len());
}

#[cfg(test)]
mod tests {
    use super::*;

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
}