"""Turn the single workshop counting bug on or off without editing the test."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app" / "app.js"
FIXED = "return tasks.filter(task => !task.completed).length;"
BUGGY = "return tasks.length;"


def set_bug(mode: str) -> bool:
    if mode not in ("on", "off"):
        raise ValueError("Bug mode must be on or off.")
    source = APP_FILE.read_bytes()
    target = (BUGGY if mode == "on" else FIXED).encode()
    previous = (FIXED if mode == "on" else BUGGY).encode()
    if source.count(target) == 1 and source.count(previous) == 0:
        return False
    if source.count(previous) != 1 or source.count(target) != 0:
        raise RuntimeError("App source differs from the workshop code; no file was changed.")
    APP_FILE.write_bytes(source.replace(previous, target, 1))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("on", "off"))
    args = parser.parse_args()
    changed = set_bug(args.mode)
    print(f"Counter bug {'is now' if changed else 'is already'} {args.mode}. Rerun the test; its expectation stays 1.")


if __name__ == "__main__":
    main()
