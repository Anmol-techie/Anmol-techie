#!/usr/bin/env python3
"""Count lines committed by the account owner across all of their repositories.

Why not the GitHub API: /repos/{o}/{r}/stats/contributors only ever reports the
DEFAULT branch. Measured on this account, project-beacon shows 49,611 additions
on `main` but 572,895 across all branches, because active work sits on a feature
branch. So we bare-clone (git log --numstat needs real blobs) and read all refs.

Commits are deduplicated by SHA across repositories, so a project that was
re-pushed to a second repo while sharing history is counted once.

Usage: count-lines.py <workdir> [--json]
"""
import json
import os
import subprocess
import sys

USER_LOGIN = "Anmol-techie"
AUTHOR_PATTERNS = ["jainanmol", USER_LOGIN]

# Count only recognised source/markup/doc files -- the approach cloc and tokei
# take. An allowlist is the only rule that generalises here: blocklisting
# generated artefacts one by one misses the next data dump someone commits
# (measured: ORM migration snapshots and script output JSON accounted for
# ~900k lines across these repos, none of it authored).
SOURCE_GLOBS = [
    "*.ts", "*.tsx", "*.js", "*.jsx", "*.mjs", "*.cjs",
    "*.py", "*.rb", "*.php", "*.go", "*.rs", "*.java", "*.kt", "*.swift",
    "*.c", "*.cc", "*.cpp", "*.h", "*.hpp", "*.cs",
    "*.sh", "*.bash", "*.zsh",
    "*.sql", "*.prisma", "*.graphql", "*.proto",
    "*.css", "*.scss", "*.sass", "*.less",
    "*.html", "*.vue", "*.svelte", "*.astro",
    "*.yaml", "*.yml", "*.toml",
    "*.md", "*.mdx",
]

# Generated or vendored files that still carry a source extension.
EXCLUDES = [
    "**/node_modules/**", "**/dist/**", "**/build/**", "**/.next/**",
    "**/out/**", "**/coverage/**", "**/vendor/**", "**/__pycache__/**",
    "**/generated/**", "**/__snapshots__/**", "**/migrations/meta/**",
    "**/*.min.js", "**/*.min.css", "**/*.map", "**/*.snap",
    "**/*.generated.*", "**/*.d.ts",
]


def run(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def owned_repos():
    rc, out, err = run(["gh", "api", "user/repos?per_page=100&affiliation=owner",
                        "--jq", ".[] | select(.fork==false) | .full_name"])
    if rc != 0:
        sys.exit(f"could not list repos: {err[:300]}")
    return [l for l in out.splitlines() if l.strip()]


def numstat(repo_dir, pathspec):
    """Return {sha: additions} for the owner's commits, honouring pathspec."""
    args = ["git", "log", "--all", "--no-merges",
            "--pretty=format:\x01%H", "--numstat"]
    for pat in AUTHOR_PATTERNS:
        args.append(f"--author={pat}")
    if pathspec:
        args += ["--"] + pathspec
    rc, out, _ = run(args, cwd=repo_dir)
    if rc != 0:
        return {}
    per_sha, sha = {}, None
    for line in out.splitlines():
        if line.startswith("\x01"):
            sha = line[1:].strip()
            per_sha.setdefault(sha, 0)
            continue
        if not line or sha is None:
            continue
        col = line.split("\t")
        # Binary files report "-" for added/removed; skip them.
        if len(col) >= 1 and col[0].isdigit():
            per_sha[sha] += int(col[0])
    return per_sha


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    if not argv:
        sys.exit("usage: count-lines.py <workdir> [--json]")
    work = argv[0]
    os.makedirs(work, exist_ok=True)

    rc, token, _ = run(["gh", "auth", "token"])
    token = token.strip()
    if rc != 0 or not token:
        sys.exit("no gh token available")

    repos = owned_repos()
    if not as_json:
        print(f"repos to scan: {len(repos)}\n", flush=True)

    raw_by_sha, code_by_sha, per_repo, failed = {}, {}, [], []

    for full in repos:
        d = os.path.join(work, full.replace("/", "_") + ".git")
        if not os.path.isdir(d):
            rc, _, err = run(["git", "clone", "--bare", "--quiet",
                              f"https://x-access-token:{token}@github.com/{full}.git", d])
            if rc != 0:
                failed.append(full)
                continue

        raw = numstat(d, None)
        code = numstat(d, SOURCE_GLOBS + [f":(exclude){p}" for p in EXCLUDES])

        new_code = 0
        for sha, add in code.items():
            if sha not in code_by_sha:
                code_by_sha[sha] = add
                new_code += add
        for sha, add in raw.items():
            raw_by_sha.setdefault(sha, add)

        if raw:
            per_repo.append({
                "repo": full,
                "raw": sum(raw.values()),
                "code": sum(code.values()),
                "code_new_after_dedupe": new_code,
                "commits": len(raw),
            })

    per_repo.sort(key=lambda r: -r["code"])
    total_code = sum(code_by_sha.values())
    total_raw = sum(raw_by_sha.values())

    if as_json:
        print(json.dumps({
            "total_code": total_code, "total_raw": total_raw,
            "unique_commits": len(raw_by_sha), "repos": per_repo,
            "clone_failed": failed,
        }, indent=2))
        return

    print(f"{'CODE+':>12} {'RAW+':>12} {'DEDUPED+':>12} {'COMMITS':>8}  REPO")
    for r in per_repo:
        print(f"{r['code']:>12,} {r['raw']:>12,} {r['code_new_after_dedupe']:>12,} "
              f"{r['commits']:>8,}  {r['repo']}")

    dupe = sum(r["code"] for r in per_repo) - total_code
    print(f"\nunique commits        : {len(raw_by_sha):,}")
    print(f"RAW additions         : {total_raw:,}")
    print(f"shared-history overlap removed : {dupe:,}")
    if failed:
        print(f"clone failed ({len(failed)}) : {failed}")
    print(f"CODE additions (source files only, generated excluded) : {total_code:,}")
    print("DONE")


if __name__ == "__main__":
    main()
