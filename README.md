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
⏳ loading · 🎙️ ready · 🔴 recording · ✍️ transcribing.

Two ways to dictate with **Right Option (⌥)** — pick whichever fits the moment:

- **Hold-to-talk:** hold ⌥, speak, release. Recording stops and the text is typed
  at your cursor. Best for quick phrases.
- **Double-tap toggle:** double-tap ⌥ to start hands-free recording, double-tap
  again to stop. Best for long, hands-free dictation.

Quit from the menu-bar dropdown.

## Styles (vocal theming)

The menu-bar **Style** submenu transforms the transcript before it's typed. The
choice persists across launches (`~/.config/yap/config.json`).

- **plain** — verbatim from the model (default)
- **lowercase** — all lowercase, sf-tech-bro aesthetic
- **uppercase** — ALL CAPS

Add your own in `yap/styles.py`: any `str -> str` function dropped into `STYLES`
shows up in the menu automatically.

## Run in the background (no terminal)

Build a menu-bar app wrapper and launch it without a terminal. You can build it
straight into /Applications:

```sh
uv run scripts/build_app.py /Applications
open /Applications/yap.app
```

`yap.app` is a thin wrapper that runs this checkout's venv — it is not
self-contained, so keep the project in place and re-run the build after moving it
or recreating `.venv`. Logs go to `~/Library/Logs/yap.log`.

**Autostart at login:** System Settings → General → Login Items → **+** → add
`yap.app`.

**Permissions:** the app has its own identity (separate from your terminal), so
grant it Microphone, Input Monitoring, and Accessibility on first launch. If
Accessibility is missing, the menu bar shows **⚠️** with buttons to open the
settings pane and to relaunch. macOS caches trust per launch, so you **must
relaunch** (use the "Relaunch yap" menu item) after enabling it.

The build ad-hoc **codesigns** the bundle so the permission grant survives moving
the app and rebuilding. If you ever granted an *unsigned* build and it got stuck,
clear the stale grants once, then rebuild:

```sh
tccutil reset Accessibility com.cluttered-cabinet.yap
tccutil reset ListenEvent com.cluttered-cabinet.yap
tccutil reset Microphone com.cluttered-cabinet.yap
```

## How it works

```
hold/2-tap ⌥  →  mic capture  →  log-mel  →  parakeet-mlx  →  keystrokes
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
