"""Dictation engine: double-tap toggle, transcription loop, and live state.

Double-tap the toggle key (Right Option) to start recording; double-tap again to
stop, transcribe, and type the result at the cursor. Speak as long as you like
between taps.

Threading model (three threads):
  - listener thread  : pynput keyboard listener -> on_press/_toggle. Touches only
                       the recorder, the queue, and `state`. Never MLX.
  - engine thread    : run() creates the Transcriber and runs _consume(). ALL MLX
                       work stays here -- MLX streams are thread-local, so the
                       thread that builds the model must also use it.
  - UI/main thread   : reads `state` to drive a menu-bar indicator (see menubar).

`state` is a plain string written from the listener/engine threads and read from
the UI thread; single attribute assignments are atomic enough for a status flag.
"""

from __future__ import annotations

import queue
import time

import numpy as np
from pynput import keyboard

from .audio import Recorder
from .inject import type_text
from .stt import SAMPLE_RATE, Transcriber

# Right Option: produces no character when tapped alone, so it's a safe toggle key.
DEFAULT_TOGGLE = keyboard.Key.alt_r

# Two taps within this window count as a double-tap (seconds).
DOUBLE_TAP_WINDOW = 0.4

# Ignore recordings shorter than this (seconds).
MIN_DURATION = 0.3

# Engine states (also the keys the UI maps to icons).
LOADING = "loading"
IDLE = "idle"
RECORDING = "recording"
TRANSCRIBING = "transcribing"


class Engine:
    def __init__(self, toggle_key: keyboard.Key = DEFAULT_TOGGLE) -> None:
        self.toggle = toggle_key
        self.recorder = Recorder(SAMPLE_RATE)
        self.transcriber: Transcriber | None = None  # built on the engine thread
        self.state = LOADING
        self._recording = False
        self._last_tap = float("-inf")  # monotonic ts of previous tap; -inf = none yet
        self._q: queue.Queue[np.ndarray | None] = queue.Queue()
        self._listener: keyboard.Listener | None = None

    # --- listener thread -------------------------------------------------

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
            self.recorder.start()
            self.state = RECORDING
            print("* recording (double-tap to stop)", flush=True)
            return
        self._recording = False
        samples = self.recorder.stop()
        dur = samples.size / SAMPLE_RATE
        if dur < MIN_DURATION:
            self.state = IDLE
            print(f"  (ignored {dur:.2f}s recording)", flush=True)
            return
        self.state = TRANSCRIBING
        self._q.put(samples)

    def start_listener(self) -> None:
        self._listener = keyboard.Listener(on_press=self.on_press)
        self._listener.start()

    # --- engine thread ---------------------------------------------------

    def run(self) -> None:
        """Build the model on THIS thread, then consume until stopped.

        The caller MUST run this on a dedicated thread that is never reused for
        other MLX work (the model's stream lives on this thread).
        """
        if self.transcriber is None:
            self.transcriber = Transcriber()
        self.state = IDLE
        self._consume()

    def _consume(self) -> None:
        while True:
            samples = self._q.get()
            if samples is None:  # shutdown sentinel
                return
            self.state = TRANSCRIBING
            text = self.transcriber.transcribe(samples)
            print(f"  -> {text!r}", flush=True)
            if text:
                type_text(text)
            self.state = IDLE

    def stop(self) -> None:
        self._q.put(None)
        if self._listener is not None:
            self._listener.stop()
