"""Output style transforms, config persistence, and engine application."""

from __future__ import annotations

import numpy as np

from yap import config
from yap.app import Engine
from yap.styles import DEFAULT_STYLE, STYLES, apply_style

# --- transforms -----------------------------------------------------------


def test_lowercase_style():
    assert apply_style("lowercase", "Hello World. It's ME!") == "hello world. it's me!"


def test_plain_style_is_identity():
    s = "Mixed Case, Untouched."
    assert apply_style("plain", s) == s


def test_unknown_style_falls_back_to_plain():
    s = "Leave Me Alone"
    assert apply_style("does-not-exist", s) == s


def test_default_style_registered():
    assert DEFAULT_STYLE in STYLES


# --- config persistence ---------------------------------------------------


def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PATH", tmp_path / "config.json")
    assert config.get("style", "plain") == "plain"  # missing file -> default
    config.set("style", "lowercase")
    assert config.get("style") == "lowercase"


def test_config_corrupt_file_is_safe(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    p.write_text("{not valid json")
    monkeypatch.setattr(config, "PATH", p)
    assert config.load() == {}


# --- engine applies the style --------------------------------------------


class FakeTranscriber:
    def transcribe(self, samples: np.ndarray) -> str:
        return "Hello There"


def test_consume_applies_style(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "PATH", tmp_path / "config.json")
    typed: list[str] = []
    monkeypatch.setattr("yap.app.type_text", lambda t: typed.append(t))
    engine = Engine()
    engine.transcriber = FakeTranscriber()
    engine.set_style("lowercase")
    engine._q.put(np.ones(16000, dtype=np.float32))
    engine._q.put(None)
    engine._consume()
    assert typed == ["hello there"]


def test_set_style_ignores_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "PATH", tmp_path / "config.json")
    engine = Engine()
    before = engine.style
    engine.set_style("nonsense")
    assert engine.style == before
