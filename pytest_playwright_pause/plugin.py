"""Pause a Playwright page after the test, before fixture teardown.

`pytest --playwright-pause` calls `page.pause()` while fixtures that depend
on `page` are still up. Those fixtures often own the test server, database
session, or auth state the inspector needs.

The `page` fixture is rebuilt from `context.new_page()` so `--browser`
parametrization keeps working. See
https://github.com/microsoft/playwright-pytest/issues/172

Set `PWDEBUG=1` and pass `-s` so `page.pause()` opens the Playwright inspector.
"""

import logging
from collections.abc import Generator
from typing import cast

import pytest
from playwright.sync_api import BrowserContext, Page

log = logging.getLogger(__name__)

# playwright treats 0 as no timeout, so the inspector is not closed at 30s
INSPECTOR_TIMEOUT_MS = 0

# long enough to watch an action while stepping through a test
PAUSE_SLOWMO_MS = 500


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--playwright-pause",
        action="store_true",
        default=False,
        help="After each test using page, call page.pause() (use PWDEBUG=1 for inspector)",
    )


def _playwright_pause_enabled(config: pytest.Config) -> bool:
    return bool(getattr(config.option, "playwright_pause", False))


def pytest_configure(config: pytest.Config) -> None:
    if _playwright_pause_enabled(config):
        config.option.headed = True
        config.option.slowmo = PAUSE_SLOWMO_MS


def _funcargs(item: pytest.Item) -> dict[str, object]:
    funcargs = getattr(item, "funcargs", None)
    if isinstance(funcargs, dict):
        return cast(dict[str, object], funcargs)

    return {}


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_teardown(
    item: pytest.Item, nextitem: pytest.Item | None
) -> Generator[None, None, None]:
    """Pause before fixture teardown so the page's server and auth are still up.

    Fixture teardown is LIFO. A fixture that depends on `page` runs its
    teardown before `page` does, and that is usually what shuts down the app
    under test. `tryfirst` runs this before other teardown hookwrappers.
    """

    del nextitem

    if _playwright_pause_enabled(item.config) and "page" in _funcargs(item):
        _pause_page(item)

    yield


def _pause_page(item: pytest.Item) -> None:
    funcargs = _funcargs(item)
    context = cast(BrowserContext | None, funcargs.get("context"))
    page = cast(Page, funcargs["page"])

    if context:
        context.set_default_timeout(INSPECTOR_TIMEOUT_MS)
        context.set_default_navigation_timeout(INSPECTOR_TIMEOUT_MS)

    log.info("pausing playwright page %s", item.nodeid)
    page.pause()


@pytest.fixture
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Open a page from `context` so multi-browser parametrization still applies.

    Requesting pytest-playwright's `page` from an override drops `--browser`
    parametrization on older pytest-playwright releases.
    """

    yield context.new_page()
