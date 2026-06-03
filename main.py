"""yap — local double-tap voice dictation.

Run with: uv run main.py

Double-tap Right Option to start recording; double-tap again to stop, transcribe,
and type the result at the cursor. A menu-bar icon shows the current state.

Requires (System Settings > Privacy & Security):
  - Microphone        access for your terminal
  - Input Monitoring  access for your terminal (to detect the toggle key)
  - Accessibility     access for your terminal (to synthesize keystrokes)
"""

from yap.app import Engine
from yap.menubar import MenuBar
from yap.perms import is_trusted, request_trust


def preflight() -> bool:
    """Ensure Accessibility trust so the shortcut is system-wide. Returns ok."""
    if is_trusted():
        return True
    print(
        "\n  yap is NOT trusted for Accessibility.\n"
        "  Until it is, the shortcut only works while this terminal is focused,\n"
        "  and typing into other apps won't work.\n",
        flush=True,
    )
    request_trust()  # pops the macOS dialog and adds your terminal to the list
    print(
        "  A system dialog should have appeared. To fix:\n"
        "    1. System Settings > Privacy & Security > Accessibility\n"
        "    2. Enable the toggle for your terminal app (e.g. Ghostty)\n"
        "    3. Also enable it under Privacy & Security > Input Monitoring\n"
        "    4. Fully quit and reopen the terminal, then re-run: uv run main.py\n",
        flush=True,
    )
    return False


def main() -> None:
    if not preflight():
        return
    print("Starting yap — the model loads in the background.", flush=True)
    print("Watch the menu bar: ⏳ loading, 🎙️ ready, 🔴 recording, ✍️ transcribing.", flush=True)
    MenuBar(Engine()).start()


if __name__ == "__main__":
    main()
