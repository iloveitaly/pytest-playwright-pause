"""Tests for the playwright pause plugin."""

from importlib.metadata import entry_points
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pytest_playwright_pause.plugin import (
    PAUSE_SLOWMO_MS,
    _playwright_pause_enabled,
    page,
    pytest_configure,
    pytest_runtest_teardown,
)


def _config(*, enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        option=SimpleNamespace(playwright_pause=enabled, headed=False, slowmo=0)
    )


def _item(
    *,
    enabled: bool,
    funcargs: dict[str, object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        config=_config(enabled=enabled),
        funcargs={} if funcargs is None else funcargs,
        nodeid="tests/test_app.py::test_login",
    )


def test_entry_point_is_registered() -> None:
    "pytest discovers the plugin through the pytest11 entry point"

    eps = entry_points(group="pytest11")
    matched = [ep for ep in eps if ep.name == "playwright_pause"]

    assert len(matched) == 1
    assert matched[0].value == "pytest_playwright_pause.plugin"


def test_pause_flag_defaults_off() -> None:
    "a config without the flag does not enable the pause"

    config = SimpleNamespace(option=SimpleNamespace())

    assert _playwright_pause_enabled(config) is False


def test_configure_sets_headed_and_slowmo_when_enabled() -> None:
    "the flag forces a headed browser and slow motion"

    config = _config(enabled=True)

    pytest_configure(config)

    assert config.option.headed is True
    assert config.option.slowmo == PAUSE_SLOWMO_MS


def test_configure_leaves_launch_options_alone_when_disabled() -> None:
    "headed and slowmo stay at their defaults when the flag is off"

    config = _config(enabled=False)

    pytest_configure(config)

    assert config.option.headed is False
    assert config.option.slowmo == 0


def test_teardown_pauses_page_and_clears_timeouts() -> None:
    "pause runs and timeouts are cleared when the test used page and context"

    page_obj = Mock()
    context = Mock()
    item = _item(
        enabled=True,
        funcargs={"page": page_obj, "context": context},
    )

    list(pytest_runtest_teardown(item, None))

    context.set_default_timeout.assert_called_once_with(0)
    context.set_default_navigation_timeout.assert_called_once_with(0)
    page_obj.pause.assert_called_once_with()


def test_teardown_pauses_without_context() -> None:
    "a test that only has page still pauses"

    page_obj = Mock()
    item = _item(enabled=True, funcargs={"page": page_obj})

    list(pytest_runtest_teardown(item, None))

    page_obj.pause.assert_called_once_with()


def test_teardown_skips_pause_when_disabled() -> None:
    "the hook does not pause when the flag is off"

    page_obj = Mock()
    item = _item(enabled=False, funcargs={"page": page_obj, "context": Mock()})

    list(pytest_runtest_teardown(item, None))

    page_obj.pause.assert_not_called()


def test_teardown_skips_pause_without_page() -> None:
    "tests that never requested page are left alone"

    item = _item(enabled=True, funcargs={"tmp_path": Mock()})

    list(pytest_runtest_teardown(item, None))


def test_teardown_ignores_items_without_funcargs() -> None:
    "collectors that never built funcargs are skipped"

    item = SimpleNamespace(config=_config(enabled=True), nodeid="tests/test_app.py")

    list(pytest_runtest_teardown(item, None))


def test_page_fixture_opens_a_page_from_context() -> None:
    "page is created from context so browser parametrization still applies"

    context = Mock()
    context.new_page.return_value = "opened-page"

    # pytest refuses direct fixture calls; the wrapped function is the body
    generator = page.__wrapped__(context)

    assert next(generator) == "opened-page"
    with pytest.raises(StopIteration):
        next(generator)
    context.new_page.assert_called_once_with()


def test_help_lists_the_flag(pytester: pytest.Pytester) -> None:
    "pytest --help documents --playwright-pause"

    result = pytester.runpytest("--help")

    result.stdout.fnmatch_lines(["*--playwright-pause*"])


def test_flag_enables_headed_and_slowmo(pytester: pytest.Pytester) -> None:
    "an inner pytest run picks up headed mode and the slowmo value"

    pytester.makepyfile(
        """
        def test_options(pytestconfig):
            assert pytestconfig.getoption("headed") is True
            assert pytestconfig.getoption("slowmo") == 500
        """
    )

    result = pytester.runpytest("--playwright-pause")

    result.assert_outcomes(passed=1)


def test_without_flag_launch_options_stay_default(pytester: pytest.Pytester) -> None:
    "headed and slowmo stay off unless the flag is passed"

    pytester.makepyfile(
        """
        def test_options(pytestconfig):
            assert pytestconfig.getoption("headed") is False
            assert pytestconfig.getoption("slowmo") == 0
        """
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_pause_runs_before_fixture_teardown(pytester: pytest.Pytester) -> None:
    "page.pause() runs after the test body and before fixture teardown"

    pytester.makepyfile(
        """
        from pathlib import Path

        import pytest

        order_path = Path("order.txt")


        class PausePage:
            def pause(self) -> None:
                order_path.write_text(order_path.read_text() + "pause\\n")


        @pytest.fixture
        def page():
            yield PausePage()
            order_path.write_text(order_path.read_text() + "teardown\\n")


        def test_paused(page):
            order_path.write_text("call\\n")
        """
    )

    result = pytester.runpytest("--playwright-pause")

    result.assert_outcomes(passed=1)
    assert (pytester.path / "order.txt").read_text() == "call\npause\nteardown\n"


def test_pause_is_skipped_without_the_flag(pytester: pytest.Pytester) -> None:
    "fixture teardown still runs when the flag is absent"

    pytester.makepyfile(
        """
        from pathlib import Path

        import pytest

        order_path = Path("order.txt")


        class PausePage:
            def pause(self) -> None:
                order_path.write_text(order_path.read_text() + "pause\\n")


        @pytest.fixture
        def page():
            yield PausePage()
            order_path.write_text(order_path.read_text() + "teardown\\n")


        def test_paused(page):
            order_path.write_text("call\\n")
        """
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)
    assert (pytester.path / "order.txt").read_text() == "call\nteardown\n"
