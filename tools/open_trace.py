"""Open a saved trace locally. Passing a folder selects its newest trace.zip."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def locate_trace(selection: str) -> Path:
    if selection == "latest":
        folders = [ROOT / "test-results", ROOT / "evidence"]
        candidates = [path for folder in folders if folder.exists() for path in folder.rglob("trace.zip")]
    else:
        target = Path(selection)
        if not target.is_absolute():
            target = ROOT / target
        candidates = [target] if target.is_file() and target.suffix == ".zip" else list(target.rglob("trace.zip"))
    if not candidates:
        raise FileNotFoundError(
            "No trace found. Run the deliberate failing test first, or use python tools/verify.py bug."
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", nargs="?", default="latest", help="latest, an evidence folder, or a trace ZIP")
    args = parser.parse_args()
    try:
        trace = locate_trace(args.selection)
    except FileNotFoundError as error:
        parser.exit(1, f"{error}\n")
    print(f"Opening saved trace: {trace}", flush=True)
    return subprocess.call([sys.executable, "-m", "playwright", "show-trace", str(trace)], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
