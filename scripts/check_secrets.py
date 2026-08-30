"""Small dependency-free guard against accidentally committed credentials."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".tools",
    "__pycache__",
    "node_modules",
}

PATTERNS = {
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Bearer token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    "Assigned secret": re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|channel[_-]?secret|password)"
        r"\s*[:=]\s*['\"]?(?!\$\{|example\b|placeholder\b|changeme\b)[^\s'\"#]{12,}"
    ),
}

SAFE_ASSIGNED_REFERENCE = re.compile(
    r"(?i)[:=]\s*(?:session|settings|config|state)\.[A-Za-z_][A-Za-z0-9_]*[,;)]?$"
)


def candidate_files(root: Path):
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            check=True,
            capture_output=True,
        )
        paths = (root / item for item in result.stdout.decode().split("\0") if item)
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
        paths = root.rglob("*")
    for path in paths:
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.name == ".env.example" or path.stat().st_size > 1_000_000:
            continue
        yield path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    findings: list[tuple[Path, str]] = []
    for path in candidate_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in PATTERNS.items():
            matches = list(pattern.finditer(text))
            if label == "Assigned secret":
                matches = [
                    match
                    for match in matches
                    if not SAFE_ASSIGNED_REFERENCE.search(match.group(0))
                ]
            if matches:
                findings.append((path.relative_to(root), label))

    if findings:
        for path, label in findings:
            print(f"Potential secret: {path} ({label})")
        return 1

    print("Secret scan passed: no supported credential patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
