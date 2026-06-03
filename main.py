"""yap — local voice dictation for macOS.

Run with: uv run main.py  (or build a background app: uv run scripts/build_app.py)

Hold Right Option to dictate (release to stop), or double-tap it to toggle
hands-free recording. Transcription is on-device; the result is typed at the
cursor. A menu-bar icon shows the state.

Permissions (System Settings > Privacy & Security): Microphone, Input Monitoring,
and Accessibility. If Accessibility is missing, the menu bar shows ⚠️ with a
button to open the right settings pane.
"""

from yap.app import Engine
from yap.menubar import MenuBar


def main() -> None:
    print("Starting yap — menu bar: ⏳ loading · 🎙️ ready · 🔴 recording · ✍️ transcribing.", flush=True)
    MenuBar(Engine()).start()


if __name__ == "__main__":
    main()
