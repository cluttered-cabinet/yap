"""Double-tap-to-toggle dictation loop.

Double-tap the toggle key (Right Option) to start recording a message; double-tap
again to stop, transcribe, and paste at the cursor. No key holding -- speak as
long as you like between taps.

Threading note: MLX streams are thread-local, so all model work MUST stay on the
thread that built the Transcriber. The keyboard listener therefore runs in the
background and the transcription loop consumes on the calling (main) thread. The
listener callbacks only touch the recorder and a queue -- never MLX.
"""

from __future__ import annotations

import queue
import time

import numpy as np
from pynput import keyboard

from .audio import Recorder
from .inject import paste_text
from .stt import Transcriber

# Right Option: produces no character when tapped alone, so it's a safe toggle key.
DEFAULT_TOGGLE = keyboard.Key.alt_r

# Two taps within this window count as a double-tap (seconds).
DOUBLE_TAP_WINDOW = 0.4

# Ignore recordings shorter than this (seconds).
MIN_DURATION = 0.3


class App:
    def __init__(self, transcriber: Transcriber, toggle_key: keyboard.Key = DEFAULT_TOGGLE) -> None:
        self.transcriber = transcriber
        self.recorder = Recorder(transcriber.sample_rate)
        self.toggle = toggle_key
        self._recording = False
        self._last_tap = float("-inf")  # monotonic ts of previous tap; -inf = none yet
        # Sentinel-terminated; consumed on the main thread (see run()).
        self._q: queue.Queue[np.ndarray | None] = queue.Queue()

    def _consume(self) -> None:
        """Run on the main thread; never spawn this elsewhere (MLX is thread-bound)."""
        while True:
            samples = self._q.get()
            if samples is None:  # shutdown sentinel
                return
            dur = samples.size / self.transcriber.sample_rate
            print(f"  transcribing {dur:.1f}s ...", flush=True)
            text = self.transcriber.transcribe(samples)
            print(f"  -> {text!r}", flush=True)
            if text:
                paste_text(text)

    def on_press(self, key) -> None:  # noqa: ANN001
        if key != self.toggle:
            return
        now = time.monotonic()
        if now - self._last_tap <= DOUBLE_TAP_WINDOW:
            self._last_tap = float("-inf")  # consume: a third quick tap won't retrigger
            self._toggle()
        else:
            self._last_tap = now

    def _toggle(self) -> None:
        if not self._recording:
            self._recording = True
            print("* recording (double-tap Right Option to stop)", flush=True)
            self.recorder.start()
            return
        self._recording = False
        samples = self.recorder.stop()
        dur = samples.size / self.transcriber.sample_rate
        if dur < MIN_DURATION:
            print(f"  (ignored {dur:.2f}s recording)", flush=True)
            return
        self._q.put(samples)

    def run(self) -> None:
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        print("Double-tap Right Option (right alt) to start/stop dictation. Ctrl+C to quit.", flush=True)
        try:
            self._consume()
        except KeyboardInterrupt:
            print("\nbye", flush=True)
        finally:
            listener.stop()
