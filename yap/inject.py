"""Insert transcribed text into the focused app.

Strategy: write to the system clipboard, then synthesize Cmd+V. Pasting is far
faster and more reliable than synthesizing each keystroke, and it preserves
Unicode (accents, CJK) that per-character typing mangles.

The prior clipboard contents are restored after pasting so dictation doesn't
clobber whatever the user had copied.
"""

from __future__ import annotations

import subprocess
import time

from pynput.keyboard import Controller, Key

_kb = Controller()


def _get_clipboard() -> str:
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


def _set_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def paste_text(text: str, restore_clipboard: bool = True) -> None:
    if not text:
        return
    saved = _get_clipboard() if restore_clipboard else None
    _set_clipboard(text)
    # Give the pasteboard a beat to settle before the keystroke.
    time.sleep(0.05)
    with _kb.pressed(Key.cmd):
        _kb.press("v")
        _kb.release("v")
    if saved is not None:
        # Let the target app read the pasteboard before we put the old value back.
        time.sleep(0.15)
        _set_clipboard(saved)
