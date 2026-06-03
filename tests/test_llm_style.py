"""Tests for the LLM-powered 'clean' style."""

from __future__ import annotations

import numpy as np

from yap import config
from yap.app import CLEANING, IDLE, Engine
from yap.styles import STYLES, apply_style


def test_clean_style_registered():
    assert "clean" in STYLES


def test_clean_style_with_mock_llm(monkeypatch):
    """Verify the clean style delegates to llm.cleanup."""
    monkeypatch.setattr("yap.llm.cleanup", lambda t: "cleaned: " + t)
    # Re-import not needed; the style calls _llm_cleanup which is bound to
    # yap.llm.cleanup at import time.  Monkeypatch the function the style
    # actually calls.
    monkeypatch.setattr("yap.styles._llm_cleanup", lambda t: "cleaned: " + t)
    assert apply_style("clean", "um hello uh world") == "cleaned: um hello uh world"


def test_cleanup_empty_passthrough(monkeypatch):
    """Empty and whitespace-only input should pass through without loading."""
    from yap import llm

    monkeypatch.setattr(llm, "_model", None)
    monkeypatch.setattr(llm, "_tokenizer", None)
    assert llm.cleanup("") == ""
    assert llm.cleanup("   ") == "   "
    # Model should NOT have been loaded.
    assert llm._model is None


class FakeTranscriber:
    def transcribe(self, samples: np.ndarray) -> str:
        return "um so like hello there"


def test_engine_enters_cleaning_state(monkeypatch, tmp_path):
    """With the 'clean' style, the engine should transition through CLEANING."""
    monkeypatch.setattr(config, "PATH", tmp_path / "config.json")
    typed: list[str] = []
    monkeypatch.setattr("yap.app.type_text", lambda t: typed.append(t))
    # Mock the LLM cleanup to avoid loading a real model.
    monkeypatch.setattr("yap.styles._llm_cleanup", lambda t: "hello there")

    states_seen: list[str] = []

    engine = Engine()
    engine.transcriber = FakeTranscriber()
    engine.set_style("clean")

    # Intercept state changes.
    original_setattr = engine.__class__.__setattr__

    def tracking_setattr(self, name, value):
        original_setattr(self, name, value)
        if name == "state":
            states_seen.append(value)

    monkeypatch.setattr(Engine, "__setattr__", tracking_setattr)

    engine._q.put(np.ones(16000, dtype=np.float32))
    engine._q.put(None)
    engine._consume()

    assert CLEANING in states_seen
    assert typed == ["hello there"]
    # Should end idle.
    assert engine.state == IDLE
