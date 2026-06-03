"""yap — local double-tap voice dictation.

Run with: uv run main.py

Double-tap Right Option to start recording; double-tap again to stop, transcribe,
and paste at the cursor.

Requires (System Settings > Privacy & Security):
  - Microphone        access for your terminal
  - Input Monitoring  access for your terminal (to detect the toggle key)
  - Accessibility     access for your terminal (to synthesize keystrokes)
"""

from yap.app import App
from yap.perms import is_trusted, request_trust
from yap.stt import Transcriber


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
    print("Loading model (first run downloads ~1.2GB) ...", flush=True)
    transcriber = Transcriber()
    print("Model ready.", flush=True)
    App(transcriber).run()


if __name__ == "__main__":
    main()
