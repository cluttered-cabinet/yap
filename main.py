"""yap — local voice dictation for macOS.

Run with: uv run main.py

Hold Right Option to dictate (release to stop), or double-tap it to toggle
hands-free recording. Transcription is on-device; the result is typed at the
cursor. A menu-bar item ("yap") shows the state.

Grant your terminal app (System Settings > Privacy & Security): Microphone,
Input Monitoring, and Accessibility. If they're missing, the menu shows ⚠️ with
a button to open the right pane; grant, then restart.
"""

from yap.app import Engine
from yap.menubar import MenuBar


def main() -> None:
    print("Starting yap — menu bar: ⏳ loading · yap ready · 🔴 recording · ✍ transcribing.", flush=True)
    MenuBar(Engine()).start()


if __name__ == "__main__":
    main()
