# Campus Tasks — Playwright with Python

A local teaching demo for third-year CS students: write a browser test, watch it run, diagnose an intentional application bug, repair it, and check the wider suite.

The server, tests, and workshop tools use Python. The small browser frontend remains HTML, CSS, and JavaScript. Tests use Playwright's **synchronous Python API** with **pytest**.

## 1. Set up once

Install Python **3.12 or later**, then open PowerShell in this `campus-tasks-python` folder, where `requirements.txt` lives.

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install
.\.venv\Scripts\python.exe -m playwright --version
```

If the first command reports an older Python, select an installed supported version when creating the environment, for example `py -3.12 -m venv .venv`.

Every Windows command below calls the virtual environment's interpreter directly. **Activation is unnecessary**, so there is no PowerShell execution-policy step. Packages and browser downloads need internet access or an appropriate existing cache. After setup, the demo runs locally.

On macOS/Linux, create the environment with `python3 -m venv .venv` and replace `.\.venv\Scripts\python.exe` below with `./.venv/bin/python`. On Linux, install browser system dependencies with `./.venv/bin/python -m playwright install --with-deps`.

## 2. Watch your first test

```powershell
.\.venv\Scripts\python.exe -m pytest -k remaining_count --headed --slowmo 350
```

The test creates **Submit assignment** and **Revise DBMS**, then completes the first task. It checks that the checkbox is selected and **1** task remains unfinished. `--headed` displays the browser; `--slowmo 350` slows operations for the audience. Slowing the demonstration is separate from adding sleeps to test code.

The supplied fixture starts the local Python server automatically, or reuses a matching server from this same project. It stops a server it started when the session finishes. The default address is `http://127.0.0.1:4173`.

## 3. Record a Python draft

For manual exploration and Codegen, keep the app running in **terminal A**:

```powershell
.\.venv\Scripts\python.exe server.py
```

Open [Campus Tasks](http://127.0.0.1:4173). In **terminal B**, from this same project folder:

```powershell
.\.venv\Scripts\python.exe -m playwright codegen --target python-pytest http://127.0.0.1:4173
```

Add a task and review the generated Python. Keep meaningful actions, choose clear locators, and add assertions for the expected outcome. Keep practice recordings outside `tests/` while reproducing the eight-case baseline. Stop the manually launched server with **Ctrl+C** when finished.

## 4. Inspect execution

This Python package uses **pytest, a visible browser, Playwright Inspector, and Trace Viewer**. Playwright Test's **UI Mode is the JavaScript/TypeScript runner interface**; it does not run this pytest suite.

To step through the selected regression in Inspector:

```powershell
.\.venv\Scripts\python.exe tools/debug_test.py
```

Use Inspector's step and resume controls, inspect the locator, and compare the browser state with the assertion. The helper sets `PWDEBUG` only for its child process; subsequent ordinary runs are unaffected.

For saved evidence, use the trace helper after a failure has produced a trace:

```powershell
.\.venv\Scripts\python.exe tools/open_trace.py latest
```

A trace records the execution. Selecting an earlier snapshot does not rewind the live app.

## 5. Break the app, then repair it

The delivered application is fixed. To demonstrate the counting defect:

```powershell
.\.venv\Scripts\python.exe tools/toggle_bug.py on
.\.venv\Scripts\python.exe -m pytest -k remaining_count --headed --slowmo 350
```

**Expected teaching failure:** the test expects `1`, but the app renders `2`. The bug changes only the return expression in `app/app.js`:

```javascript
// Intentional bug: counts every record, including completed tasks.
return tasks.length;

// Correct rule: count unfinished tasks.
return tasks.filter(task => !task.completed).length;
```

Read the assertion failure and open its saved trace. Confirm that completing a task leaves both records present, so total length is the wrong quantity. Keep the test's expected value unchanged.

Restore the correct expression and rerun:

```powershell
.\.venv\Scripts\python.exe tools/toggle_bug.py off
.\.venv\Scripts\python.exe -m pytest -k remaining_count --headed --slowmo 350
```

The guarded toggle helper accepts only the recognised expressions. If you stop the lesson while the bug is enabled, run `tools/toggle_bug.py off` before the next normal session.

## 6. Run the full suite and open its report

```powershell
.\.venv\Scripts\python.exe -m pytest --browser chromium --browser firefox --browser webkit --html=reports/report.html --self-contained-html
Start-Process .\reports\report.html
```

The baseline contains **8 scenarios × 3 browsers = 24 planned executions**: adding, whitespace rejection, completion/count, filtering, editing, deleting, clearing completed tasks, and reload persistence. A plain `-m pytest` run uses Chromium by default.

`pytest.ini` enables an HTML report and keeps traces/screenshots for failures. The HTML file summarises outcomes; trace ZIPs and screenshot files remain in the results directory. Keep those files when sharing diagnostic evidence. This is a **pytest-html report**, not Playwright Test's JavaScript HTML reporter.

## Collect a complete evidence set

```powershell
.\.venv\Scripts\python.exe tools/verify.py
.\.venv\Scripts\python.exe tools/open_trace.py evidence/intentional-failure
Start-Process .\evidence\matrix\report.html
```

The verification helper runs the browser matrix, three separate Chromium repetitions, the intentional failure, and the repaired regression. It restores the app in a `finally` block. Do not edit the app while it is running.

Each run has its own `report.html`, `result.json`, `terminal.txt`, and `results/` directory. `evidence/summary.json` records actual versions, counts, statuses, and source evidence. Use that file and the reports for observed results; the planned counts above are not a substitute for executing this Python version.

For a smaller verification job, pass `matrix`, `repeat`, or `bug` to `tools/verify.py`. Repeated runs can reveal stability issues; repeated success does not prove that every defect is absent.

## Files worth knowing

| File | Purpose |
|---|---|
| `server.py` | Local Python web server |
| `app/app.js` | Browser application behaviour, including the counter |
| `tests/test_tasks.py` | Eight Python test scenarios |
| `conftest.py` | Shared fixtures and local-server lifecycle |
| `pytest.ini` | Test discovery and default evidence settings |
| `requirements.txt` | Python dependency versions |
| `PRESENTER_GUIDE.md` | A 70-minute classroom walkthrough |

## Troubleshooting

- **`py` is unavailable:** install Python with its Windows launcher, or use a supported Python executable to create `.venv`.
- **Import or plugin error:** use the exact `.venv` interpreter above and reinstall `requirements.txt` into that environment.
- **Browser executable missing:** run `.\.venv\Scripts\python.exe -m playwright install` after installing requirements.
- **Port 4173 is occupied:** identify the existing process. The tests deliberately reject a different app or a different source copy on this port. Stop that conflicting server before running this package.
- **No tests collected:** run from this package folder and check the `tests/` directory and any `-k` selection.
- **Inspector appears paused:** use its resume/step controls; pausing is expected during a debugging run.
- **No trace found:** passing runs normally discard failure-only traces. First execute the intentional failure or the verification helper.

## CI example and references

`.github/workflows/playwright.yml` installs Python dependencies and browsers on a Linux runner, runs the 24-execution matrix, and uploads reports even after a failure. It assumes this package is the repository root. It is a supplied example; no hosted workflow run is claimed.

- [Playwright Python installation](https://playwright.dev/python/docs/intro)
- [Python test writing](https://playwright.dev/python/docs/writing-tests)
- [Pytest plugin and command options](https://playwright.dev/python/docs/test-runners)
- [Python Codegen](https://playwright.dev/python/docs/codegen)
- [Inspector debugging](https://playwright.dev/python/docs/debug)
- [Trace Viewer](https://playwright.dev/python/docs/trace-viewer)
- [Python CI](https://playwright.dev/python/docs/ci)
- [pytest-html reports](https://pytest-html.readthedocs.io/en/latest/user_guide.html)
