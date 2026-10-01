"""Optional answers, excluded from the eight-test baseline.

Run separately: python -m pytest exercises
"""

from playwright.sync_api import Page, expect


def add_task(page: Page, text: str) -> None:
    page.get_by_label("New task").fill(text)
    page.get_by_role("button", name="Add task").click()


def test_unchecking_restores_an_active_task_and_count(page: Page) -> None:
    add_task(page, "Read OS")
    add_task(page, "Write SQL")
    first = page.get_by_role("checkbox", name="Complete Read OS", exact=True)
    second = page.get_by_role("checkbox", name="Complete Write SQL", exact=True)
    first.check()
    second.check()
    expect(page.get_by_test_id("remaining-count")).to_have_text("0")
    first.uncheck()
    expect(page.get_by_test_id("remaining-count")).to_have_text("1")
    page.get_by_role("button", name="Active", exact=True).click()
    expect(page.get_by_test_id("task-title")).to_have_text(["Read OS"])


def test_shows_a_controlled_study_tip_response(page: Page) -> None:
    page.route("**/api/study-tip", lambda route: route.fulfill(
        json={"tip": "Mocked tip: review your failing assertion."}
    ))
    page.get_by_role("button", name="Get study tip").click()
    expect(page.get_by_role("status")).to_have_text("Mocked tip: review your failing assertion.")


def test_displays_the_real_local_study_tip_response(page: Page) -> None:
    page.get_by_role("button", name="Get study tip").click()
    expect(page.get_by_role("status")).to_have_text("Break large tasks into smaller steps.")
