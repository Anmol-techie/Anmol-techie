#!/usr/bin/env python3
"""Rewrite the lines-committed badge in README.md between the LOC markers.

Usage: write-badge.py "543,555"
"""
import re
import sys

README = "README.md"
START, END = "<!--LOC:START-->", "<!--LOC:END-->"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: write-badge.py <count-with-commas>", file=sys.stderr)
        return 2

    count = sys.argv[1].strip()
    if not count.replace(",", "").isdigit():
        print(f"not a number: {count!r}", file=sys.stderr)
        return 1

    # shields.io needs the comma percent-encoded or it reads as a field break.
    encoded = count.replace(",", "%2C")
    badge = (
        f'<img src="https://img.shields.io/badge/Lines%20Committed-{encoded}'
        '-38BDF8?style=for-the-badge&logo=git&logoColor=white" alt="Lines committed"/>'
    )

    src = open(README, encoding="utf-8").read()
    if START not in src or END not in src:
        print(f"markers {START}/{END} not found in {README}", file=sys.stderr)
        return 1

    out = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        f"{START}\n  {badge}\n  {END}",
        src,
        flags=re.S,
    )
    open(README, "w", encoding="utf-8").write(out)
    print(f"badge set to {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
