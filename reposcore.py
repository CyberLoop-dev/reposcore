#!/usr/bin/env python3
"""reposcore: score the health of a repository from 0 to 100.

Pure standard library. Run `reposcore --help` for usage.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

__version__ = "0.1.0"

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".tox", ".mypy_cache", ".idea", ".vscode",
}
MAX_BYTES = 1_000_000

README_NAMES = {"readme.md", "readme", "readme.rst", "readme.txt"}
LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "copying.md", "unlicense"}
MANIFESTS = {
    "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "pipfile",
    "package.json", "go.mod", "cargo.toml", "gemfile", "pom.xml",
    "build.gradle", "composer.json",
}
TEST_DIRS = {"tests", "test", "__tests__", "spec"}
TEST_SUFFIXES = ("_test.py", "_test.go", ".test.js", ".test.ts", ".spec.js", ".spec.ts", "test.java")

SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "Slack token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "Hardcoded credential": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*['\"][A-Za-z0-9/+_\-]{20,}['\"]"
    ),
}


@dataclass
class Check:
    name: str
    points: int
    max_points: int
    detail: str

    @property
    def passed(self) -> bool:
        return self.points == self.max_points


def collect_files(root: Path) -> list[str]:
    """Return repo-relative POSIX paths, skipping vendor and cache folders."""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            rel = Path(dirpath, name).relative_to(root).as_posix()
            found.append(rel)
    return sorted(found)


def read_text(path: Path) -> str | None:
    """Read a text file, or return None for binary or oversized files."""
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:2048]:
        return None
    return data.decode("utf-8", errors="ignore")


def _root_files(rels: list[str]) -> list[str]:
    return [r for r in rels if "/" not in r]


def check_readme_exists(root: Path, rels: list[str]) -> Check:
    ok = any(r.lower() in README_NAMES for r in _root_files(rels))
    return Check("README present", 10 if ok else 0, 10, "found" if ok else "no README at repo root")


def check_readme_quality(root: Path, rels: list[str]) -> Check:
    name = next((r for r in _root_files(rels) if r.lower() in README_NAMES), None)
    text = read_text(root / name) if name else None
    if not text:
        return Check("README quality", 0, 10, "nothing to evaluate")
    points, notes = 0, []
    if len(text.strip()) >= 500:
        points += 4
    else:
        notes.append("under 500 characters")
    if len(re.findall(r"^#{1,6}\s", text, re.M)) >= 3:
        points += 3
    else:
        notes.append("fewer than 3 headings")
    if "```" in text:
        points += 3
    else:
        notes.append("no code block")
    return Check("README quality", points, 10, "; ".join(notes) or "length, headings and code block")


def check_license(root: Path, rels: list[str]) -> Check:
    ok = any(r.lower() in LICENSE_NAMES for r in _root_files(rels))
    return Check("License", 10 if ok else 0, 10, "found" if ok else "no LICENSE file")


def check_tests(root: Path, rels: list[str]) -> Check:
    for rel in rels:
        parts = rel.lower().split("/")
        base = parts[-1]
        if TEST_DIRS & set(parts[:-1]) or base.startswith("test_") or base.endswith(TEST_SUFFIXES):
            return Check("Tests", 15, 15, f"e.g. {rel}")
    return Check("Tests", 0, 15, "no test files found")


def check_ci(root: Path, rels: list[str]) -> Check:
    for rel in rels:
        low = rel.lower()
        if (low.startswith(".github/workflows/") and low.endswith((".yml", ".yaml"))) or low in (
            ".gitlab-ci.yml", ".circleci/config.yml", "azure-pipelines.yml",
        ):
            return Check("CI configured", 15, 15, f"e.g. {rel}")
    return Check("CI configured", 0, 15, "no CI workflow found")


def check_gitignore(root: Path, rels: list[str]) -> Check:
    ok = ".gitignore" in rels
    return Check(".gitignore", 5 if ok else 0, 5, "found" if ok else "missing")


def check_docs(root: Path, rels: list[str]) -> Check:
    for rel in rels:
        low = rel.lower()
        if low.startswith(("contributing", "changelog")) or low.startswith("docs/"):
            return Check("Contributing or docs", 5, 5, f"e.g. {rel}")
    return Check("Contributing or docs", 0, 5, "no CONTRIBUTING, CHANGELOG or docs/")


def check_manifest(root: Path, rels: list[str]) -> Check:
    for rel in _root_files(rels):
        if rel.lower() in MANIFESTS:
            return Check("Dependency manifest", 10, 10, f"found {rel}")
    return Check("Dependency manifest", 0, 10, "no manifest at repo root")


def find_secrets(root: Path, rels: list[str]) -> list[tuple[str, int, str]]:
    findings = []
    for rel in rels:
        text = read_text(root / rel)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if "reposcore:ignore" in line:
                continue
            for kind, pattern in SECRET_PATTERNS.items():
                if pattern.search(line):
                    findings.append((rel, lineno, kind))
                    break
    return findings


def check_secrets(root: Path, rels: list[str]) -> Check:
    findings = find_secrets(root, rels)
    points = max(0, 20 - 10 * len(findings))
    if not findings:
        return Check("No leaked secrets", 20, 20, "none found")
    shown = ", ".join(f"{p}:{n} ({k})" for p, n, k in findings[:3])
    more = f" (+{len(findings) - 3} more)" if len(findings) > 3 else ""
    return Check("No leaked secrets", points, 20, f"{len(findings)} possible: {shown}{more}")


CHECKS = [
    check_readme_exists, check_readme_quality, check_license, check_tests, check_ci,
    check_gitignore, check_docs, check_manifest, check_secrets,
]


def grade_for(score: int) -> str:
    for cutoff, letter in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if score >= cutoff:
            return letter
    return "F"


def scan(root: Path) -> dict:
    root = Path(root).resolve()
    rels = collect_files(root)
    checks = [fn(root, rels) for fn in CHECKS]
    score = sum(c.points for c in checks)
    return {
        "root": str(root),
        "score": score,
        "grade": grade_for(score),
        "checks": [{**asdict(c), "passed": c.passed} for c in checks],
    }


def badge_svg(score: int, label: str = "repo score") -> str:
    value = f"{score}/100"
    color = (
        "#4c1" if score >= 90 else "#97ca00" if score >= 80
        else "#dfb317" if score >= 70 else "#fe7d37" if score >= 60 else "#e05d44"
    )
    lw, vw = 7 * len(label) + 12, 7 * len(value) + 12
    w = lw + vw
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" '
        f'aria-label="{label}: {value}"><title>{label}: {value}</title>'
        '<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/></linearGradient>'
        f'<clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>'
        f'<g clip-path="url(#r)"><rect width="{lw}" height="20" fill="#555"/>'
        f'<rect x="{lw}" width="{vw}" height="20" fill="{color}"/>'
        f'<rect width="{w}" height="20" fill="url(#s)"/></g>'
        '<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="{lw / 2:g}" y="14">{label}</text><text x="{lw + vw / 2:g}" y="14">{value}</text></g></svg>\n'
    )


def render_report(result: dict) -> str:
    lines = [f"reposcore {__version__}  -  {result['root']}", ""]
    for c in result["checks"]:
        mark = "[x]" if c["passed"] else "[~]" if c["points"] else "[ ]"
        lines.append(f"  {mark} {c['name']:<22} {c['points']:>2}/{c['max_points']:<2}  {c['detail']}")
    lines += ["", f"Score: {result['score']}/100  (grade {result['grade']})"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reposcore", description="Score repository health from 0 to 100.")
    parser.add_argument("path", nargs="?", default=".", help="repository folder (default: current directory)")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--badge", metavar="FILE", help="write an SVG score badge to FILE")
    parser.add_argument("--min-score", type=int, default=0, metavar="N", help="exit with code 1 if score is below N")
    parser.add_argument("--version", action="version", version=f"reposcore {__version__}")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"reposcore: not a directory: {args.path}", file=sys.stderr)
        return 2

    result = scan(root)
    if args.badge:
        Path(args.badge).write_text(badge_svg(result["score"]), encoding="utf-8")
    print(json.dumps(result, indent=2) if args.json else render_report(result))
    return 1 if result["score"] < args.min_score else 0


if __name__ == "__main__":
    sys.exit(main())
