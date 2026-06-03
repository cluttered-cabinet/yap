# yap

Local, private voice dictation for macOS (Apple Silicon). Double-tap a key, speak,
double-tap again — your words get transcribed on-device and pasted at the cursor.
No cloud, no account.

Transcription runs entirely on-device via [`parakeet-mlx`](https://github.com/senstella/parakeet-mlx)
(NVIDIA Parakeet TDT 0.6B v3) on Apple's MLX runtime.

## Requirements

- Apple Silicon Mac, macOS 14+
- [uv](https://docs.astral.sh/uv/)
- Grant your terminal these permissions in **System Settings → Privacy & Security**:
  - **Microphone** — capture audio
  - **Input Monitoring** — detect the toggle key
  - **Accessibility** — synthesize keystrokes to type at the cursor

## Usage

```sh
uv run main.py
```

First run downloads the model (~1.2 GB). A menu-bar icon shows the state:
⏳ loading · 🎙️ ready · 🔴 recording · ✍️ transcribing. Then:

1. **Double-tap Right Option (⌥)** to start recording (icon turns 🔴).
2. Speak as long as you like.
3. **Double-tap Right Option** again to stop — the text is transcribed (✍️) and
   typed wherever your cursor is.

Quit from the menu-bar dropdown.

## How it works

```
double-tap ⌥  →  mic capture  →  log-mel  →  parakeet-mlx  →  keystrokes
(listener      (sounddevice,     (in-RAM,    (on-device      (typed at cursor,
 thread)        16 kHz mono)      no temp     MLX/Metal,       clipboard never
                                  files)      engine thread)   touched)
```

Three threads: the menu bar (AppKit) owns the main thread, the engine builds and
runs the model on its own thread (MLX streams are thread-local), and the keyboard
listener runs in the background. A timer polls engine state to update the icon.

## Development

```sh
uv run pytest
```

## License

MIT
