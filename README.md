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
  - **Accessibility** — synthesize Cmd+V to paste

## Usage

```sh
uv run main.py
```

First run downloads the model (~1.2 GB). Then:

1. **Double-tap Right Option (⌥)** to start recording.
2. Speak as long as you like.
3. **Double-tap Right Option** again to stop — the text is transcribed and pasted
   wherever your cursor is.

`Ctrl+C` to quit.

## How it works

```
double-tap ⌥  →  mic capture  →  log-mel  →  parakeet-mlx  →  clipboard + ⌘V
(keyboard      (sounddevice,     (in-RAM,    (on-device      (restores prior
 listener)      16 kHz mono)      no temp     MLX/Metal)       clipboard)
                                  files)
```

The keyboard listener runs in the background; all MLX work stays on the main
thread (MLX streams are thread-local).

## Development

```sh
uv run pytest
```

## License

MIT
