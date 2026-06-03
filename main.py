"""yap — local double-tap voice dictation.

Run with: uv run main.py

Double-tap Right Option to start recording; double-tap again to stop, transcribe,
and paste at the cursor.

Requires (System Settings > Privacy & Security):
  - Microphone        access for your terminal
  - Input Monitoring  access for your terminal (to detect the toggle key)
  - Accessibility     access for your terminal (to synthesize Cmd+V)
"""

from yap.app import App
from yap.stt import Transcriber


def main() -> None:
    print("Loading model (first run downloads ~1.2GB) ...", flush=True)
    transcriber = Transcriber()
    print("Model ready.", flush=True)
    App(transcriber).run()


if __name__ == "__main__":
    main()
