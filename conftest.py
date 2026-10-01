"""Local server, isolated Playwright pages, and a small JSON evidence summary."""

from __future__ import annotations

import json
import os
import platform
import threading
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

import pytest
from playwright.sync_api import Page

from server import APP_ID, HOST, ROOT, configured_port, make_server

_cases: dict[str, dict] = {}
_started_at = ""
_started_clock = 0.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _health(url: str) -> dict | None:
    try:
        with build_opener(ProxyHandler({})).open(url + "/health", timeout=2) as response:
            return json.load(response)
    except (URLError, OSError, ValueError):
        return None


def _is_our_server(health: dict | None) -> bool:
    return (
        isinstance(health, dict)
        and health.get("appId") == APP_ID
        and isinstance(health.get("sourceRoot"), str)
        and os.path.normcase(health.get("sourceRoot", "")) == os.path.normcase(str(ROOT))
    )


@pytest.fixture(scope="session")
def campus_server():
    """Reuse this folder's server, or start and stop our own local server."""
    port = configured_port()
    url = f"http://{HOST}:{port}"
    if _is_our_server(_health(url)):
        yield url
        return
    try:
        server = make_server(port)
    except OSError as error:
        raise RuntimeError(
            f"Port {port} is occupied by a different app or a different copy of this lab. "
            "Stop that server, or set CAMPUS_PORT consistently before starting this lab."
        ) from error
    thread = threading.Thread(target=server.serve_forever, name="campus-tasks-server", daemon=True)
    thread.start()
    try:
        if not _is_our_server(_health(url)):
            raise RuntimeError("The local Campus Tasks health check did not pass.")
        yield url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="session")
def base_url(campus_server):
    return campus_server


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, base_url):
    return {**browser_context_args, "base_url": base_url, "viewport": {"width": 1280, "height": 800}}


@pytest.fixture(autouse=True)
def open_app(page: Page, campus_server):
    # pytest-playwright supplies a fresh context and page for every test.
    page.goto("/")


def pytest_sessionstart(session):
    global _started_at, _started_clock
    _cases.clear()
    _started_at = _utc_now()
    _started_clock = time.monotonic()


def pytest_runtest_logreport(report):
    case = _cases.setdefault(report.nodeid, {"nodeid": report.nodeid, "phases": {}, "durationSeconds": 0.0})
    case["phases"][report.when] = report.outcome
    case["durationSeconds"] += report.duration
    if report.failed:
        case.setdefault("failures", []).append({"phase": report.when, "message": report.longreprtext})


def pytest_sessionfinish(session, exitstatus):
    cases = []
    for case in _cases.values():
        phases = case["phases"]
        if phases.get("setup") == "failed" or phases.get("teardown") == "failed":
            outcome = "error"
        elif phases.get("call") == "failed":
            outcome = "failed"
        elif "skipped" in phases.values():
            outcome = "skipped"
        elif phases.get("call") == "passed":
            outcome = "passed"
        else:
            outcome = "incomplete"
        cases.append({**case, "outcome": outcome})
    packages = {}
    for name in ("playwright", "pytest", "pytest-playwright", "pytest-html"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    result = {
        "startedAt": _started_at,
        "finishedAt": _utc_now(),
        "durationSeconds": time.monotonic() - _started_clock,
        "exitCode": int(exitstatus),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "counts": {outcome: sum(case["outcome"] == outcome for case in cases)
                   for outcome in ("passed", "failed", "error", "skipped", "incomplete")},
        "executions": len(cases),
        "collected": session.testscollected,
        "cases": cases,
    }
    path = Path(os.environ.get("CAMPUS_RESULT_JSON", str(ROOT / "reports" / "result.json")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
