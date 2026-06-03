# yap

Local, private voice dictation for macOS (Apple Silicon). Hold a key, speak, and
your words are transcribed **on-device** and typed wherever your cursor is. No
cloud, no account.

Transcription runs entirely on-device via
[`parakeet-mlx`](https://github.com/senstella/parakeet-mlx) (NVIDIA Parakeet TDT
0.6B v3) on Apple's MLX runtime.

## Requirements

- Apple Silicon Mac, macOS 14+
- [uv](https://docs.astral.sh/uv/)

## Setup

```sh
git clone https://github.com/cluttered-cabinet/yap.git
cd yap
uv sync
```

Grant your **terminal app** (Terminal, iTerm, Ghostty, …) these permissions in
**System Settings → Privacy & Security**:

- **Microphone** — capture audio
- **Input Monitoring** — detect the dictation key
- **Accessibility** — type at the cursor

(yap runs from your terminal, so the permissions attach to the terminal, not to
yap itself. The first run also prompts you.)

## Usage

```sh
uv run main.py
```

First run downloads the model (~1.2 GB). A menu-bar item shows the state:
**yap ⏳** loading · **yap** ready · **yap 🔴** recording · **yap ✍** transcribing.
(If you see **yap ⚠️**, Accessibility isn't granted yet — use the menu's "Open
Accessibility Settings…", enable your terminal, and restart.)

Two ways to dictate with **Right Option (⌥)**:

- **Hold-to-talk** — hold ⌥, speak, release. Best for quick phrases.
- **Double-tap toggle** — double-tap ⌥ to start hands-free recording, double-tap
  again to stop. Best for long dictation.

Quit from the menu-bar dropdown (or Ctrl+C in the terminal).

## Styles (vocal theming)

The menu-bar **Style** submenu transforms the transcript before it's typed; the
choice persists across runs (`~/.config/yap/config.json`):

- **plain** — verbatim (default)
- **lowercase** — all lowercase
- **uppercase** — ALL CAPS

Add your own in `yap/styles.py`: any `str -> str` function in `STYLES` shows up
in the menu automatically.

## How it works

```
hold/2-tap ⌥  →  mic capture  →  log-mel  →  parakeet-mlx  →  keystrokes
(listener      (sounddevice,     (in-RAM,    (on-device      (typed at cursor,
 thread)        16 kHz mono)      no temp     MLX/Metal,       clipboard never
                                  files)      engine thread)   touched)
```

Three threads: the menu bar (AppKit) owns the main thread, the engine builds and
runs the model on its own thread (MLX streams are thread-local), and the keyboard
listener runs in the background.

## Development

```sh
uv run pytest
```

## License

MIT
