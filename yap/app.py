"""Dictation engine: hold-to-talk + double-tap toggle, transcription, live state.

Two ways to dictate with the same key (Right Option):
  - Hold-to-talk : press and hold; recording starts once the key has been held
                   past HOLD_THRESHOLD (this is what separates a hold from a tap);
                   release to stop, transcribe, and type.
  - Double-tap   : two quick taps start hands-free recording; two more stop it.

A short press that is released before HOLD_THRESHOLD is a "tap" and feeds the
double-tap detector. A tap never starts the microphone, so double-tapping doesn't
thrash the input stream.

Threading model (four threads):
  - listener thread : pynput on_press/on_release. Touches recorder/queue/state.
  - hold timer      : a threading.Timer per press; fires once to promote a held
                      key into a recording. Guarded by the same lock as the
                      listener so release-vs-timer races are serialized.
  - engine thread   : run() builds the Transcriber and runs _consume(). ALL MLX
                      work stays here -- MLX streams are thread-local.
  - UI/main thread  : reads `state` to drive the menu-bar indicator.

`state` is a plain string written from listener/timer/engine threads and read
from the UI thread; single attribute assignments are atomic enough for a flag.
"""

from __future__ import annotations

import queue
import threading
import time

import numpy as np
from pynput import keyboard

from . import config
from .audio import Recorder
from .inject import type_text
from .stt import SAMPLE_RATE, Transcriber
from .styles import DEFAULT_STYLE, STYLES, apply_style

# Styles that use the LLM (show a separate "cleaning" state in the UI).
_LLM_STYLES = frozenset({"clean"})

# Right Option: produces no character when tapped alone, so it's a safe key.
DEFAULT_TOGGLE = keyboard.Key.alt_r

# Held at least this long => hold-to-talk; released sooner => a tap. (seconds)
HOLD_THRESHOLD = 0.2

# Two taps within this window count as a double-tap. (seconds)
DOUBLE_TAP_WINDOW = 0.4

# Ignore recordings shorter than this. (seconds)
MIN_DURATION = 0.3

# Engine states (also the keys the UI maps to icons).
LOADING = "loading"
IDLE = "idle"
RECORDING = "recording"
TRANSCRIBING = "transcribing"
CLEANING = "cleaning"

# Active-recording modes.
_HOLD = "hold"
_TOGGLE = "toggle"


class Engine:
    def __init__(self, toggle_key: keyboard.Key = DEFAULT_TOGGLE) -> None:
        self.toggle = toggle_key
        self.recorder = Recorder(SAMPLE_RATE)
        self.transcriber: Transcriber | None = None  # built on the engine thread
        self.style = config.get("style", DEFAULT_STYLE)  # vocal theming
        self.state = LOADING
        self._mode: str | None = None  # None | _HOLD | _TOGGLE
        self._down = False  # toggle key physically held right now
        self._press_time = 0.0
        self._last_tap = float("-inf")  # monotonic ts of previous tap; -inf = none
        self._hold_timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._q: queue.Queue[np.ndarray | None] = queue.Queue()
        self._listener: keyboard.Listener | None = None

    # --- listener / timer threads ---------------------------------------

    def on_press(self, key) -> None:  # noqa: ANN001
        if key != self.toggle:
            return
        with self._lock:
            if self._down:  # ignore key-repeat
                return
            self._down = True
            self._press_time = time.monotonic()
            # Arm hold detection only when nothing is recording yet.
            if self._mode is None:
                self._hold_timer = threading.Timer(HOLD_THRESHOLD, self._hold_fired)
                self._hold_timer.start()

    def _hold_fired(self) -> None:
        with self._lock:
            if self._down and self._mode is None:
                self._mode = _HOLD
                self._start_recording()

    def on_release(self, key) -> None:  # noqa: ANN001
        if key != self.toggle:
            return
        with self._lock:
            if not self._down:
                return
            self._down = False
            now = time.monotonic()
            held = now - self._press_time
            if self._hold_timer is not None:
                self._hold_timer.cancel()
                self._hold_timer = None

            if self._mode == _HOLD:  # push-to-talk end
                self._mode = None
                self._finish_recording()
                return

            if held > HOLD_THRESHOLD:
                # A long press that didn't become a hold recording (e.g. while a
                # toggle recording is already running) -- not a tap, ignore.
                return

            # A tap: feed the double-tap detector.
            if now - self._last_tap <= DOUBLE_TAP_WINDOW:
                self._last_tap = float("-inf")  # consume
                if self._mode == _TOGGLE:  # double-tap stops hands-free recording
                    self._mode = None
                    self._finish_recording()
                else:  # double-tap starts hands-free recording
                    self._mode = _TOGGLE
                    self._start_recording()
            else:
                self._last_tap = now

    def _start_recording(self) -> None:
        self.recorder.start()
        self.state = RECORDING
        print("* recording", flush=True)

    def _finish_recording(self) -> None:
        samples = self.recorder.stop()
        dur = samples.size / SAMPLE_RATE
        if dur < MIN_DURATION:
            self.state = IDLE
            print(f"  (ignored {dur:.2f}s recording)", flush=True)
            return
        self.state = TRANSCRIBING
        self._q.put(samples)

    def start_listener(self) -> None:
        self._listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
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

    def set_style(self, name: str) -> None:
        """Switch the output style and persist it. Unknown names are ignored."""
        if name not in STYLES:
            return
        self.style = name
        config.set("style", name)

    def _consume(self) -> None:
        while True:
            samples = self._q.get()
            if samples is None:  # shutdown sentinel
                return
            self.state = TRANSCRIBING
            raw = self.transcriber.transcribe(samples)
            if self.style in _LLM_STYLES:
                self.state = CLEANING
            text = apply_style(self.style, raw)
            print(f"  -> {text!r}", flush=True)
            if text:
                type_text(text)
            self.state = IDLE

    def stop(self) -> None:
        self._q.put(None)
        if self._listener is not None:
            self._listener.stop()
