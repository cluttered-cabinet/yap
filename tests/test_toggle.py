"""Engine gestures: hold-to-talk, double-tap toggle, and the consume loop.

The hold timer and clock are faked so press/hold/release sequences are fully
deterministic (no real wall-clock waits, no real threading.Timer firing).
"""

from __future__ import annotations

import numpy as np
import pytest
from pynput import keyboard

from yap.app import (
    DOUBLE_TAP_WINDOW,
    IDLE,
    RECORDING,
    TRANSCRIBING,
    Engine,
    _HOLD,
    _TOGGLE,
)

OTHER = keyboard.Key.shift  # a non-toggle key


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


class FakeTimer:
    """Stand-in for threading.Timer: never fires on its own; tests fire manually."""

    def __init__(self, interval, fn):  # noqa: ANN001
        self.interval = interval
        self.fn = fn
        self.cancelled = False

    def start(self) -> None:
        pass

    def cancel(self) -> None:
        self.cancelled = True


class Clock:
    def __init__(self, monkeypatch) -> None:
        self.t = 0.0
        monkeypatch.setattr("yap.app.time.monotonic", lambda: self.t)

    def at(self, t: float) -> None:
        self.t = t


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr("yap.app.threading.Timer", FakeTimer)
    clock = Clock(monkeypatch)
    engine = Engine()
    rec = FakeRecorder(16000)
    engine.recorder = rec
    return engine, rec, clock


def press(engine: Engine, clock: Clock, t: float, key=None) -> None:
    clock.at(t)
    engine.on_press(key or engine.toggle)


def release(engine: Engine, clock: Clock, t: float, key=None) -> None:
    clock.at(t)
    engine.on_release(key or engine.toggle)


def fire_hold(engine: Engine) -> None:
    """Simulate the hold timer elapsing while the key is still down."""
    engine._hold_fired()


# --- hold-to-talk ---------------------------------------------------------


def test_hold_to_talk_records_then_transcribes(env):
    engine, rec, clock = env
    press(engine, clock, 0.0)
    fire_hold(engine)
    assert engine._mode == _HOLD
    assert engine.state == RECORDING
    assert rec.started == 1
    release(engine, clock, 1.0)
    assert engine._mode is None
    assert engine.state == TRANSCRIBING
    assert rec.stopped == 1
    assert engine._q.qsize() == 1


def test_hold_too_short_is_ignored(env):
    engine, rec, clock = env
    rec._buf = np.ones(int(16000 * 0.1), dtype=np.float32)  # 0.1s < MIN_DURATION
    press(engine, clock, 0.0)
    fire_hold(engine)
    release(engine, clock, 0.25)
    assert engine.state == IDLE
    assert engine._q.qsize() == 0


def test_quick_tap_does_not_start_mic(env):
    engine, rec, clock = env
    press(engine, clock, 0.0)
    release(engine, clock, 0.05)  # released before hold timer fires
    assert rec.started == 0
    assert engine._mode is None


# --- double-tap toggle ----------------------------------------------------


def test_double_tap_starts_toggle(env):
    engine, rec, clock = env
    press(engine, clock, 0.00)
    release(engine, clock, 0.05)
    press(engine, clock, 0.10)
    release(engine, clock, 0.15)  # second tap within window
    assert engine._mode == _TOGGLE
    assert engine.state == RECORDING
    assert rec.started == 1


def test_double_tap_starts_then_stops(env):
    engine, rec, clock = env
    # start
    press(engine, clock, 0.00)
    release(engine, clock, 0.05)
    press(engine, clock, 0.10)
    release(engine, clock, 0.15)
    assert engine._mode == _TOGGLE
    # stop with another double-tap
    press(engine, clock, 5.00)
    release(engine, clock, 5.05)
    press(engine, clock, 5.10)
    release(engine, clock, 5.15)
    assert engine._mode is None
    assert engine.state == TRANSCRIBING
    assert rec.stopped == 1
    assert engine._q.qsize() == 1


def test_taps_outside_window_do_not_toggle(env):
    engine, rec, clock = env
    press(engine, clock, 0.00)
    release(engine, clock, 0.05)
    press(engine, clock, 0.05 + DOUBLE_TAP_WINDOW + 0.1)
    release(engine, clock, 0.05 + DOUBLE_TAP_WINDOW + 0.15)
    assert engine._mode is None
    assert rec.started == 0


def test_tap_then_hold_is_push_to_talk(env):
    engine, rec, clock = env
    press(engine, clock, 0.00)
    release(engine, clock, 0.05)  # a tap
    press(engine, clock, 0.10)  # then hold (within double-tap window)
    fire_hold(engine)
    assert engine._mode == _HOLD  # hold wins over double-tap
    assert engine.state == RECORDING
    release(engine, clock, 1.0)
    assert engine._mode is None
    assert engine._q.qsize() == 1


def test_other_keys_ignored(env):
    engine, rec, clock = env
    press(engine, clock, 0.0, key=OTHER)
    release(engine, clock, 0.05, key=OTHER)
    fire_hold(engine)  # no key down -> no effect
    assert rec.started == 0
    assert engine._mode is None


# --- consume loop ---------------------------------------------------------


class FakeTranscriber:
    def __init__(self, text: str) -> None:
        self._text = text

    def transcribe(self, samples: np.ndarray) -> str:
        return self._text


def test_consume_transcribes_and_types(env, monkeypatch):
    engine, _, _ = env
    typed: list[str] = []
    monkeypatch.setattr("yap.app.type_text", lambda t: typed.append(t))
    engine.transcriber = FakeTranscriber("hello world")
    engine._q.put(np.ones(16000, dtype=np.float32))
    engine._q.put(None)
    engine._consume()
    assert typed == ["hello world"]
    assert engine.state == IDLE


def test_consume_skips_empty_transcript(env, monkeypatch):
    engine, _, _ = env
    typed: list[str] = []
    monkeypatch.setattr("yap.app.type_text", lambda t: typed.append(t))
    engine.transcriber = FakeTranscriber("")
    engine._q.put(np.ones(16000, dtype=np.float32))
    engine._q.put(None)
    engine._consume()
    assert typed == []
    assert engine.state == IDLE
