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
    assert any("Accessibility" in t for t in titles)


def test_trusted_menu_builds_without_crashing():
    bar = MenuBar(Engine())
    bar._build_menu(trusted=True)  # must not raise
    # No permission affordances when trusted.
    assert not any("Relaunch" in t for t in _menu_titles(bar))


def test_style_submenu_reflects_and_switches(monkeypatch, tmp_path):
    from yap import config

    monkeypatch.setattr(config, "PATH", tmp_path / "config.json")
    engine = Engine()
    engine.set_style("plain")
    bar = MenuBar(engine)
    bar._build_style_submenu()
    assert bar._style_items["plain"].state == 1
    assert bar._style_items["lowercase"].state == 0
    # Selecting lowercase updates the engine and moves the checkmark.
    bar._select_style(bar._style_items["lowercase"])
    assert engine.style == "lowercase"
    assert bar._style_items["lowercase"].state == 1
    assert bar._style_items["plain"].state == 0
