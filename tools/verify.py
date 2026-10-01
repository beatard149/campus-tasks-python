"""Collect real matrix, repeated-run, deliberate failure and repair evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from toggle_bug import APP_FILE, BUGGY, FIXED, set_bug

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
TEST_FILE = ROOT / "tests" / "test_tasks.py"
SUMMARY_FILE = EVIDENCE / "summary.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_versions() -> dict:
    result = {}
    for name in ("playwright", "pytest", "pytest-playwright", "pytest-html"):
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = None
    return result


def browser_versions() -> list:
    """Read installed package metadata; the tests prove which browsers launched."""
    import playwright

    metadata = Path(playwright.__file__).parent / "driver" / "package" / "browsers.json"
    if not metadata.exists():
        return []
    return [entry for entry in json.loads(metadata.read_text(encoding="utf-8"))["browsers"]
            if entry["name"] in ("chromium", "firefox", "webkit")]


def save_summary(summary: dict) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    summary["updatedAt"] = utc_now()
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def run_case(summary: dict, name: str, args: list[str], expected_passed: int, expected_failed: int = 0) -> dict:
    folder = EVIDENCE / name
    folder.mkdir(parents=True, exist_ok=True)
    result_file = folder / "result.json"
    if result_file.exists():
        result_file.unlink()  # Never mistake an older JSON result for this invocation.
    output = folder / "results"
    report = folder / "report.html"
    command = [sys.executable, "-m", "pytest", *args,
               "--html", str(report), "--self-contained-html", "--output", str(output)]
    env = os.environ.copy()
    env.pop("PWDEBUG", None)
    env["PYTEST_ADDOPTS"] = ""
    env["PYTHONIOENCODING"] = "utf-8"
    env["CAMPUS_RESULT_JSON"] = str(result_file)
    started_at = utc_now()
    print(f"\n--- {name} ---", flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, encoding="utf-8", errors="replace", capture_output=True)
    terminal = result.stdout + result.stderr
    (folder / "terminal.txt").write_text(terminal, encoding="utf-8")
    print(terminal, end="", flush=True)
    actual = json.loads(result_file.read_text(encoding="utf-8")) if result_file.exists() else {}
    expected_exit = 1 if expected_failed else 0
    counts = actual.get("counts", {})
    correct = (
        result.returncode == expected_exit
        and counts.get("passed") == expected_passed
        and counts.get("failed") == expected_failed
        and counts.get("error") == 0
        and counts.get("skipped") == 0
        and counts.get("incomplete") == 0
        and actual.get("executions") == expected_passed + expected_failed
    )
    record = {
        "startedAt": started_at,
        "finishedAt": utc_now(),
        "command": ["python", "-m", "pytest", *args, "--html", f"evidence/{name}/report.html",
                    "--self-contained-html", "--output", f"evidence/{name}/results"],
        "exitCode": result.returncode,
        "expectedExit": expected_exit,
        "matchedExpectedResult": correct,
        "counts": counts,
        "executions": actual.get("executions"),
        "durationSeconds": actual.get("durationSeconds"),
        "report": f"evidence/{name}/report.html",
        "rawResult": f"evidence/{name}/result.json",
        "results": f"evidence/{name}/results",
        "traces": [str(path.relative_to(ROOT)).replace(os.sep, "/") for path in output.rglob("trace.zip")],
        "testSourceSha256": file_hash(TEST_FILE),
        "appSourceSha256": file_hash(APP_FILE),
    }
    summary["runs"][name] = record
    save_summary(summary)
    if not correct:
        raise RuntimeError(f"{name}: observed {counts}, exit {result.returncode}; expected {expected_passed} passed/{expected_failed} failed. See {report}.")
    return record


def main() -> int:
    # Windows redirected terminals may use cp1252. Keep logs UTF-8 and make
    # display-only characters safe without changing the actual saved evidence.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", nargs="?", choices=("all", "matrix", "repeat", "bug"), default="all")
    args = parser.parse_args()
    fixed_source = APP_FILE.read_bytes()
    if fixed_source.count(FIXED.encode()) != 1 or BUGGY.encode() in fixed_source:
        parser.error("Start with the fixed app: python tools/toggle_bug.py off")
    test_before = file_hash(TEST_FILE)
    previous = json.loads(SUMMARY_FILE.read_text(encoding="utf-8")) if SUMMARY_FILE.exists() else {}
    summary = {
        **previous,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": package_versions(),
        "browserPackageMetadata": browser_versions(),
        "retryPolicy": "No retries configured; each selected case runs once per pytest invocation.",
        "runs": previous.get("runs", {}),
        "notes": [
            "Actual local runs; the app and API use no external service.",
            "pytest-playwright creates a fresh context and page for each case.",
            "Python uses pytest, Playwright Inspector and Trace Viewer, not Playwright Test UI Mode.",
            "The reports are pytest-html reports, not Playwright Test HTML reports.",
            "Browser metadata records the package revisions; passing runs establish launch evidence.",
            "Repeated passing runs do not prove the absence of every defect.",
        ],
    }
    try:
        if args.phase in ("all", "matrix"):
            run_case(summary, "matrix", ["--browser", "chromium", "--browser", "firefox", "--browser", "webkit"], 24)
        if args.phase in ("all", "repeat"):
            repeats = [run_case(summary, f"repeat-chromium-{index}", ["--browser", "chromium"], 8) for index in range(1, 4)]
            summary["repeatChromiumTotal"] = {
                "invocations": 3,
                "executions": sum(run["executions"] for run in repeats),
                "passed": sum(run["counts"]["passed"] for run in repeats),
                "failed": sum(run["counts"]["failed"] for run in repeats),
            }
            save_summary(summary)
        if args.phase in ("all", "bug"):
            try:
                set_bug("on")
                intentional = run_case(summary, "intentional-failure", ["--browser", "chromium", "-k", "remaining_count"], 0, 1)
                if not intentional["traces"]:
                    raise RuntimeError("The deliberate failure did not produce a retained trace.")
            finally:
                APP_FILE.write_bytes(fixed_source)
                summary["appRestoredToFixed"] = APP_FILE.read_bytes() == fixed_source
                save_summary(summary)
            run_case(summary, "repaired-regression", ["--browser", "chromium", "-k", "remaining_count"], 1)
    finally:
        # Restoration also covers Ctrl+C or an unexpected verifier exception.
        APP_FILE.write_bytes(fixed_source)
        summary["appRestoredToFixed"] = APP_FILE.read_bytes() == fixed_source
        summary["testSourceProof"] = {
            "beforeSha256": test_before,
            "afterSha256": file_hash(TEST_FILE),
            "unchanged": file_hash(TEST_FILE) == test_before,
        }
        summary["fixedAppSha256"] = file_hash(APP_FILE)
        save_summary(summary)
    if not summary["testSourceProof"]["unchanged"]:
        raise RuntimeError("Test source changed during verification; investigate before presenting the evidence.")
    print(f"\nEvidence summary: {SUMMARY_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
