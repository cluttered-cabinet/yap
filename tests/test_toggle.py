"""Engine behavior: double-tap detection, state transitions, and the consume loop."""

from __future__ import annotations

import numpy as np
from pynput import keyboard

from yap.app import DOUBLE_TAP_WINDOW, IDLE, RECORDING, TRANSCRIBING, Engine


class FakeRecorder:
    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate
        self.started = 0
        self.stopped = 0
        self._buf = np.ones(sample_rate, dtype=np.float32)  # 1.0s, above MIN_DURATION

    def start(self) -> None:
        self.started += 1

    def stop(self) -> np.ndarray:
        self.stopped += 1
        return self._buf


OTHER = keyboard.Key.shift  # a non-toggle key


def _make_engine() -> tuple[Engine, FakeRecorder]:
    engine = Engine()
    rec = FakeRecorder(16000)
    engine.recorder = rec
    return engine, rec


def _press(engine: Engine, key, t: float, monkeypatch) -> None:
    monkeypatch.setattr("yap.app.time.monotonic", lambda: t)
    engine.on_press(key)


# --- double-tap detection -------------------------------------------------


def test_double_tap_starts_then_stops(monkeypatch):
    engine, rec = _make_engine()
    tk = engine.toggle
    _press(engine, tk, 0.00, monkeypatch)
    _press(engine, tk, 0.10, monkeypatch)
    assert engine._recording is True
    assert engine.state == RECORDING
    assert rec.started == 1 and rec.stopped == 0

    _press(engine, tk, 5.00, monkeypatch)
    _press(engine, tk, 5.10, monkeypatch)
    assert engine._recording is False
    assert engine.state == TRANSCRIBING
    assert rec.stopped == 1
    assert engine._q.qsize() == 1


def test_single_taps_do_nothing(monkeypatch):
    engine, rec = _make_engine()
    tk = engine.toggle
    _press(engine, tk, 0.00, monkeypatch)
    _press(engine, tk, 1.00, monkeypatch)  # gap > window
    _press(engine, tk, 2.00, monkeypatch)
    assert engine._recording is False
    assert rec.started == 0


def test_taps_just_outside_window_do_not_toggle(monkeypatch):
    engine, rec = _make_engine()
    tk = engine.toggle
    _press(engine, tk, 0.00, monkeypatch)
    _press(engine, tk, DOUBLE_TAP_WINDOW + 0.01, monkeypatch)
    assert engine._recording is False
    assert rec.started == 0


def test_other_keys_ignored(monkeypatch):
    engine, rec = _make_engine()
    _press(engine, OTHER, 0.00, monkeypatch)
    _press(engine, OTHER, 0.10, monkeypatch)
    assert engine._recording is False
    assert rec.started == 0


def test_triple_tap_does_not_double_toggle(monkeypatch):
    engine, rec = _make_engine()
    tk = engine.toggle
    _press(engine, tk, 0.00, monkeypatch)
    _press(engine, tk, 0.10, monkeypatch)
    _press(engine, tk, 0.20, monkeypatch)
    assert engine._recording is True
    assert rec.started == 1 and rec.stopped == 0


def test_short_recording_is_ignored(monkeypatch):
    engine, rec = _make_engine()
    rec._buf = np.ones(int(16000 * 0.1), dtype=np.float32)  # 0.1s < MIN_DURATION
    tk = engine.toggle
    _press(engine, tk, 0.00, monkeypatch)
    _press(engine, tk, 0.10, monkeypatch)  # start
    _press(engine, tk, 5.00, monkeypatch)
    _press(engine, tk, 5.10, monkeypatch)  # stop, too short
    assert engine.state == IDLE
    assert engine._q.qsize() == 0


# --- consume loop ---------------------------------------------------------


class FakeTranscriber:
    def __init__(self, text: str) -> None:
        self._text = text

    def transcribe(self, samples: np.ndarray) -> str:
        return self._text


def test_consume_transcribes_and_types(monkeypatch):
    engine, _ = _make_engine()
    typed: list[str] = []
    monkeypatch.setattr("yap.app.type_text", lambda t: typed.append(t))
    engine.transcriber = FakeTranscriber("hello world")
    engine._q.put(np.ones(16000, dtype=np.float32))
    engine._q.put(None)  # sentinel
    engine._consume()
    assert typed == ["hello world"]
    assert engine.state == IDLE


def test_consume_skips_empty_transcript(monkeypatch):
    engine, _ = _make_engine()
    typed: list[str] = []
    monkeypatch.setattr("yap.app.type_text", lambda t: typed.append(t))
    engine.transcriber = FakeTranscriber("")
    engine._q.put(np.ones(16000, dtype=np.float32))
    engine._q.put(None)
    engine._consume()
    assert typed == []
    assert engine.state == IDLE
