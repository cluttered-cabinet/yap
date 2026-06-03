"""yap — local voice dictation for macOS.

Run with: uv run yap   (or: uv run python -m yap)

Hold Right Option to dictate (release to stop), or double-tap it to toggle
hands-free recording. Transcription is on-device; the result is typed at the
cursor. A menu-bar item ("yap") shows the state.

Grant your terminal app (System Settings > Privacy & Security): Microphone,
Input Monitoring, and Accessibility. If they're missing, the menu shows yap ⚠️
with a button to open the right pane; grant, then restart.
"""

from __future__ import annotations

from .app import Engine
from .menubar import MenuBar


def main() -> None:
    print("Starting yap — watch the menu bar (yap). First run downloads the model.", flush=True)
    MenuBar(Engine()).start()
