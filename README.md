[![Release Notes](https://img.shields.io/github/release/iloveitaly/pytest-playwright-pause)](https://github.com/iloveitaly/pytest-playwright-pause/releases)
[![Downloads](https://static.pepy.tech/badge/pytest-playwright-pause/month)](https://pepy.tech/project/pytest-playwright-pause)
![GitHub CI Status](https://github.com/iloveitaly/pytest-playwright-pause/actions/workflows/build_and_publish.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# Pause a Playwright page before pytest teardown

`page.pause()` is awkward to place in a pytest-playwright suite. Put it after `yield` in the `page` fixture and pytest has already started tearing other fixtures down. Teardown is LIFO, so a server fixture, a database session, or an auth helper that depends on `page` is gone before the browser closes. The inspector is attached to a page whose app is already shut down.

`--playwright-pause` hooks `pytest_runtest_teardown` and calls `page.pause()` before that unwind.

## Installation

```bash
uv add --dev pytest-playwright-pause
```

pytest loads the plugin on its own. This package depends on `pytest-playwright`. Install browser binaries before a headed run:

```bash
uv run playwright install
```

## Usage

```bash
PWDEBUG=1 uv run pytest --playwright-pause -s
```

`PWDEBUG=1` opens the Playwright inspector. `-s` leaves stdin alone so you can drive it. The run waits on each test that requested `page` until you resume.

While the flag is set, the plugin turns on headed mode and sets slow motion to 500ms. It also sets the context timeout to 0 for the pause, because Playwright's default 30s timeout will close the inspector.

Tests that never asked for `page` are unchanged. Leave the flag off in CI.

The plugin's `page` fixture is `context.new_page()`. That keeps `--browser chromium --browser firefox` working when a `page` fixture is overridden. Older pytest-playwright dropped that parametrization: https://github.com/microsoft/playwright-pytest/issues/172

## Features

- `--playwright-pause` calls `page.pause()` before fixture teardown, with the test server and auth still up
- Headed mode and 500ms slow motion for that run
- Context timeouts cleared so the inspector is not closed at 30 seconds
- `page` comes from `context.new_page()` so multi-browser parametrization still applies

## [MIT License](LICENSE.md)

---

*This project was created from [iloveitaly/python-package-template](https://github.com/iloveitaly/python-package-template)*
