"""Insert transcribed text into the focused app via synthesized keystrokes.

We type the text directly as Unicode key events rather than using the clipboard,
so the user's clipboard is never touched (no save/restore, no clobbering images
or rich content). pynput's Controller.type emits each character through
CGEventKeyboardSetUnicodeString on macOS, which is layout-independent and handles
accents/CJK correctly.

A small per-character delay avoids dropped characters: posting events faster than
the target app drains its event queue can silently lose keystrokes in some apps.
"""

from __future__ import annotations

import time

from pynput.keyboard import Controller

_kb = Controller()

# Seconds between characters. ~0.005s is imperceptible for dictation-length text
# while staying slow enough that fast/slow apps don't drop characters.
TYPE_DELAY = 0.005


def type_text(text: str, delay: float = TYPE_DELAY) -> None:
    if not text:
        return
    for ch in text:
        _kb.type(ch)
        if delay:
            time.sleep(delay)
