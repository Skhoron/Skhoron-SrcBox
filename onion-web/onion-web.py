#!/usr/bin/env python3
# Copyright 2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Picks a random LIVE .onion site from a list you provide.

Needs: Tor running locally (Tor Browser = port 9150, tor daemon = 9050)
Install: pip install "requests[socks]"

Examples:
  python onion_random.py -a                  # random sites via Ahmia
  python onion_random.py -a -k news -k tech  # search Ahmia for these words
  python onion_random.py -f onions.txt
  python onion_random.py -f onions.txt -k news -k tech
  python onion_random.py -u https://example.com/list.txt -n 3
  python onion_random.py -f onions.txt --exclude shop --exclude market
"""
import argparse
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ONION_RE = re.compile(r"\b([a-z2-7]{56}\.onion)\b", re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def load_addresses(file_path, url, session):
    text = ""
    if file_path:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            text += f.read() + "\n"
    if url:
        text += session.get(url, timeout=60).text
    # only v3 addresses (56 chars), deduplicated
    return sorted({m.lower() for m in ONION_RE.findall(text)})


WORDS = ["news", "tech", "linux", "privacy", "security", "books", "forum", "blog",
         "music", "science", "crypto", "art", "wiki", "radio", "games", "mirror",
         "library", "chat", "email", "hosting", "journalism", "archive"]


def ahmia_addresses(terms, pages=1):
    """Collect onion addresses from Ahmia search results (clearnet request,
    Ahmia keeps its own ban list and excludes abuse material from its index)."""
    found = set()
    for term in terms:
        for page in range(pages):
            try:
                r = requests.get(
                    "https://ahmia.fi/search/",
                    params={"q": term, "page": page},
                    timeout=30,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                found.update(m.lower() for m in ONION_RE.findall(r.text))
            except Exception as e:
                print(f"[ahmia] '{term}' failed: {e}", file=sys.stderr)
    return sorted(found)


def check(addr, session, timeout):
    """Return (addr, title, body_lowercase) if alive, else None."""
    try:
        r = session.get(
            f"http://{addr}/",
            timeout=timeout,
            stream=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        body = r.raw.read(200_000, decode_content=True).decode("utf-8", "ignore")
        m = TITLE_RE.search(body)
        title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        return addr, title, body.lower()
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser(description="Random live onion site picker")
    p.add_argument("-f", "--file", help="file with onion addresses (any text)")
    p.add_argument("-u", "--url", help="URL with a list of onion addresses")
    p.add_argument("-n", "--count", type=int, default=1, help="how many to show")
    p.add_argument("-k", "--keyword", action="append", default=[],
                   help="keep only sites with this word in title/page (repeatable, any match)")
    p.add_argument("-x", "--exclude", action="append", default=[],
                   help="drop sites with this word in title/page (repeatable)")
    p.add_argument("-a", "--ahmia", action="store_true",
                   help="take addresses from Ahmia search (uses -k as search terms, "
                        "random words if no -k)")
    p.add_argument("--port", type=int, default=9150,
                   help="Tor SOCKS port (9150 Tor Browser, 9050 tor daemon)")
    p.add_argument("--timeout", type=int, default=25)
    p.add_argument("--sample", type=int, default=40,
                   help="how many random addresses to test at once")
    p.add_argument("--threads", type=int, default=10)
    args = p.parse_args()

    if not (args.file or args.url or args.ahmia):
        p.error("need -a, -f or -u")

    session = requests.Session()
    session.proxies = {
        "http": f"socks5h://127.0.0.1:{args.port}",
        "https": f"socks5h://127.0.0.1:{args.port}",
    }

    addrs = []
    try:
        if args.file or args.url:
            addrs = load_addresses(args.file, args.url, session)
        if args.ahmia:
            terms = args.keyword or random.sample(WORDS, 5)
            addrs = sorted(set(addrs) | set(ahmia_addresses(terms)))
    except Exception as e:
        sys.exit(f"Could not load list: {e}")
    if not addrs:
        sys.exit("No valid v3 onion addresses found in the list.")

    random.shuffle(addrs)
    kws = [k.lower() for k in args.keyword]
    exc = [x.lower() for x in args.exclude]
    found = 0

    # test in batches until we have enough matches or run out of addresses
    for i in range(0, len(addrs), args.sample):
        batch = addrs[i:i + args.sample]
        with ThreadPoolExecutor(max_workers=args.threads) as ex:
            futures = [ex.submit(check, a, session, args.timeout) for a in batch]
            for fut in as_completed(futures):
                res = fut.result()
                if not res:
                    continue
                addr, title, body = res
                if kws and not any(k in body for k in kws):
                    continue
                if any(x in body for x in exc):
                    continue
                print(f"http://{addr}/  |  {title or '(no title)'}")
                found += 1
                if found >= args.count:
                    return
    if not found:
        print("Nothing alive matched. Try another list or looser filters.")


if __name__ == "__main__":
    main()
