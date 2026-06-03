"""Double-tap toggle detection — the logic that decides start vs stop vs ignore."""

from __future__ import annotations

import numpy as np
from pynput import keyboard

from yap.app import DOUBLE_TAP_WINDOW, App


class FakeRecorder:
    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate
        self.started = 0
        self.stopped = 0

    def start(self) -> None:
        self.started += 1

    def stop(self) -> np.ndarray:
        self.stopped += 1
        return np.ones(self.sample_rate, dtype=np.float32)  # 1.0s, above MIN_DURATION


class FakeTranscriber:
    sample_rate = 16000


def _make_app() -> tuple[App, FakeRecorder]:
    app = App(FakeTranscriber())
    rec = FakeRecorder(16000)
    app.recorder = rec
    return app, rec


OTHER = keyboard.Key.shift  # a non-toggle key


def _press(app: App, key, t: float, monkeypatch) -> None:
    monkeypatch.setattr("yap.app.time.monotonic", lambda: t)
    app.on_press(key)


def test_double_tap_starts_then_stops(monkeypatch):
    app, rec = _make_app()
    tk = app.toggle
    # First double-tap -> start
    _press(app, tk, 0.00, monkeypatch)
    _press(app, tk, 0.10, monkeypatch)
    assert app._recording is True
    assert rec.started == 1 and rec.stopped == 0
    # Second double-tap -> stop + enqueue
    _press(app, tk, 5.00, monkeypatch)
    _press(app, tk, 5.10, monkeypatch)
    assert app._recording is False
    assert rec.stopped == 1
    assert app._q.qsize() == 1


def test_single_taps_do_nothing(monkeypatch):
    app, rec = _make_app()
    tk = app.toggle
    _press(app, tk, 0.00, monkeypatch)
    _press(app, tk, 1.00, monkeypatch)  # gap > window
    _press(app, tk, 2.00, monkeypatch)
    assert app._recording is False
    assert rec.started == 0


def test_taps_just_outside_window_do_not_toggle(monkeypatch):
    app, rec = _make_app()
    tk = app.toggle
    _press(app, tk, 0.00, monkeypatch)
    _press(app, tk, DOUBLE_TAP_WINDOW + 0.01, monkeypatch)
    assert app._recording is False
    assert rec.started == 0


def test_other_keys_ignored(monkeypatch):
    app, rec = _make_app()
    _press(app, OTHER, 0.00, monkeypatch)
    _press(app, OTHER, 0.10, monkeypatch)
    assert app._recording is False
    assert rec.started == 0


def test_triple_tap_does_not_double_toggle(monkeypatch):
    app, rec = _make_app()
    tk = app.toggle
    # Three rapid taps: taps 1+2 start; tap 3 must NOT immediately toggle again.
    _press(app, tk, 0.00, monkeypatch)
    _press(app, tk, 0.10, monkeypatch)
    _press(app, tk, 0.20, monkeypatch)
    assert app._recording is True
    assert rec.started == 1 and rec.stopped == 0
