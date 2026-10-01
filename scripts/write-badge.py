#!/usr/bin/env python3
"""Publish the lines-committed figure into README.md and assets/lines-committed.svg.

GitHub renders no line-count anywhere in its own profile UI -- the contribution
graph counts commits only -- so this is the only place the number can appear.

Usage: write-badge.py <lines> [commits] [repos]
       write-badge.py "699,450" 458 19
"""
import os
import re
import sys

README = "README.md"
SVG_PATH = os.path.join("assets", "lines-committed.svg")
START, END = "<!--LOC:START-->", "<!--LOC:END-->"

# Colours chosen to stay legible on both the light and dark GitHub themes,
# because a README image cannot know which one the viewer is using.
ACCENT = "#0EA5E9"
LABEL = "#94A3B8"
MUTED = "#64748B"
FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif")


def svg(lines: str, commits: str, repos: str, per_commit: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="820" height="210" viewBox="0 0 820 210" role="img" aria-label="{lines} source lines committed">
  <title>{lines} source lines committed</title>
  <g font-family="{FONT}" text-anchor="middle">
    <text x="410" y="40" font-size="17" font-weight="600" fill="{LABEL}" letter-spacing="3.5">SOURCE LINES COMMITTED</text>
    <text x="410" y="140" font-size="104" font-weight="800" fill="{ACCENT}" letter-spacing="-2">{lines}</text>
    <text x="410" y="178" font-size="17" fill="{MUTED}">{commits} commits &#183; {repos} repositories &#183; ~{per_commit} lines per commit</text>
  </g>
</svg>
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: write-badge.py <lines> [commits] [repos]", file=sys.stderr)
        return 2

    def as_int(raw: str):
        raw = raw.strip().replace(",", "").replace("_", "")
        return int(raw) if raw.isdigit() else None

    n_lines = as_int(sys.argv[1])
    if n_lines is None:
        print(f"not a number: {sys.argv[1]!r}", file=sys.stderr)
        return 1

    n_commits = as_int(sys.argv[2]) if len(sys.argv) > 2 else None
    n_repos = as_int(sys.argv[3]) if len(sys.argv) > 3 else None

    # Formatting happens here, not in the shell -- the caller passes plain ints.
    lines = f"{n_lines:,}"
    commits = f"{n_commits:,}" if n_commits is not None else ""
    repos = f"{n_repos:,}" if n_repos is not None else ""
    per_commit = f"{n_lines // n_commits:,}" if n_commits else ""

    os.makedirs(os.path.dirname(SVG_PATH), exist_ok=True)
    with open(SVG_PATH, "w", encoding="utf-8") as fh:
        fh.write(svg(lines, commits or "?", repos or "?", per_commit or "?"))

    src = open(README, encoding="utf-8").read()
    if START not in src or END not in src:
        print(f"markers {START}/{END} not found in {README}", file=sys.stderr)
        return 1

    block = (
        f"{START}\n\n"
        f'<img src="assets/lines-committed.svg" alt="{lines} source lines committed" width="100%"/>\n\n'
        f"{END}"
    )
    out = re.sub(re.escape(START) + r".*?" + re.escape(END), block, src, flags=re.S)
    open(README, "w", encoding="utf-8").write(out)
    print(f"wrote {lines} ({commits} commits, {repos} repos, ~{per_commit}/commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
