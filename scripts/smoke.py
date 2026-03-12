from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "agents.py",
    "tasks.py",
    "tools.py",
    "main.py",
]


def check_files() -> None:
    missing = [name for name in FILES if not (ROOT / name).exists()]
    if missing:
        raise SystemExit(f"Eksik dosyalar: {', '.join(missing)}")


def check_syntax() -> None:
    for name in FILES:
        path = ROOT / name
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))


def main() -> None:
    check_files()
    check_syntax()
    print("Smoke test basarili: dosyalar mevcut ve Python syntax dogru.")


if __name__ == "__main__":
    main()
