"""Test pytest-playwright-pause."""

import pytest_playwright_pause


def test_import() -> None:
    """Test that the  can be imported."""
    assert isinstance(pytest_playwright_pause.__name__, str)


def test_version() -> None:
    """Test that the version is available."""
    assert isinstance(pytest_playwright_pause.__version__, str)