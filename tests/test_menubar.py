"""Menu construction regression tests.

The untrusted menu once crashed with NSInternalInconsistencyException because the
status MenuItem was added to the menu twice (in __init__ and again in start()).
Building the menu must not raise, and must include the permission affordances when
untrusted.
"""

from __future__ import annotations

import pytest

rumps = pytest.importorskip("rumps")

from yap.app import Engine  # noqa: E402
from yap.menubar import MenuBar  # noqa: E402


def _menu_titles(bar: MenuBar) -> list[str]:
    return [str(k) for k in bar.menu.keys()]


def test_untrusted_menu_builds_without_crashing():
    bar = MenuBar(Engine())
    bar._build_menu(trusted=False)  # regression: must not raise
    titles = _menu_titles(bar)
    assert any("Relaunch" in t for t in titles)
    assert any("Accessibility" in t for t in titles)


def test_trusted_menu_builds_without_crashing():
    bar = MenuBar(Engine())
    bar._build_menu(trusted=True)  # must not raise
    # No permission affordances when trusted.
    assert not any("Relaunch" in t for t in _menu_titles(bar))
