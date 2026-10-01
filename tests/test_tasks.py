"""Eight independent scenarios: run with python -m pytest."""

from playwright.sync_api import Page, expect


def add_task(page: Page, text: str) -> None:
    page.get_by_label("New task").fill(text)
    page.get_by_role("button", name="Add task").click()


def test_adds_a_task_and_clears_the_input(page: Page) -> None:
    add_task(page, "Submit assignment")
    expect(page.get_by_test_id("task-title")).to_have_text(["Submit assignment"])
    expect(page.get_by_label("New task")).to_have_value("")
    expect(page.get_by_test_id("remaining-count")).to_have_text("1")


def test_rejects_whitespace_without_creating_a_task(page: Page) -> None:
    add_task(page, "   ")
    expect(page.get_by_role("alert")).to_have_text("Enter a task before adding it.")
    expect(page.get_by_test_id("task-item")).to_have_count(0)


def test_remaining_count_updates_when_a_task_is_completed(page: Page) -> None:
    add_task(page, "Submit assignment")
    add_task(page, "Revise DBMS")
    expect(page.get_by_test_id("remaining-count")).to_have_text("2")
    checkbox = page.get_by_role("checkbox", name="Complete Submit assignment", exact=True)
    checkbox.check()
    expect(checkbox).to_be_checked()
    expect(page.get_by_test_id("remaining-count")).to_have_text("1")


def test_filters_active_and_completed_tasks(page: Page) -> None:
    add_task(page, "Submit assignment")
    add_task(page, "Revise DBMS")
    page.get_by_role("checkbox", name="Complete Submit assignment", exact=True).check()
    page.get_by_role("button", name="Active", exact=True).click()
    expect(page.get_by_test_id("task-title")).to_have_text(["Revise DBMS"])
    page.get_by_role("button", name="Completed", exact=True).click()
    expect(page.get_by_test_id("task-title")).to_have_text(["Submit assignment"])
    page.get_by_role("button", name="All", exact=True).click()
    expect(page.get_by_test_id("task-title")).to_have_text(["Submit assignment", "Revise DBMS"])


def test_edits_a_task_and_removes_the_old_text(page: Page) -> None:
    add_task(page, "Revise DBMS")
    page.get_by_role("button", name="Edit Revise DBMS", exact=True).click()
    page.get_by_role("textbox", name="Edit task", exact=True).fill("Revise SQL joins")
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_test_id("task-title")).to_have_text(["Revise SQL joins"])
    expect(page.get_by_text("Revise DBMS", exact=True)).to_have_count(0)


def test_deletes_only_the_selected_task(page: Page) -> None:
    add_task(page, "Submit assignment")
    add_task(page, "Revise DBMS")
    page.get_by_role("button", name="Delete Submit assignment", exact=True).click()
    expect(page.get_by_test_id("task-title")).to_have_text(["Revise DBMS"])


def test_clears_completed_tasks_and_keeps_active_tasks(page: Page) -> None:
    add_task(page, "Submit assignment")
    add_task(page, "Revise DBMS")
    page.get_by_role("checkbox", name="Complete Submit assignment", exact=True).check()
    page.get_by_role("button", name="Clear completed", exact=True).click()
    expect(page.get_by_test_id("task-title")).to_have_text(["Revise DBMS"])
    expect(page.get_by_role("button", name="Clear completed", exact=True)).to_be_disabled()


def test_preserves_task_text_and_completion_after_reload(page: Page) -> None:
    add_task(page, "Submit assignment")
    page.get_by_role("checkbox", name="Complete Submit assignment", exact=True).check()
    page.reload()
    expect(page.get_by_test_id("task-title")).to_have_text(["Submit assignment"])
    expect(page.get_by_role("checkbox", name="Complete Submit assignment", exact=True)).to_be_checked()
