"""Open Playwright Inspector for the remaining-count test."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 1:
        print("Use: python tools/debug_test.py", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    child_env = os.environ.copy()
    child_env["PWDEBUG"] = "1"
    # This change exists only in the child process; the terminal stays unchanged.
    return subprocess.call(
        [sys.executable, "-m", "pytest", "tests/test_tasks.py", "--browser", "chromium", "-k", "remaining_count", "-s"],
        cwd=root,
        env=child_env,
    )


if __name__ == "__main__":
    raise SystemExit(main())
