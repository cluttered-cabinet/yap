"""Vocal theming: output styles applied to the transcript before it is typed.

A style is a pure ``str -> str`` transform. Add one by dropping a function into
STYLES; it shows up in the menu automatically. Insertion order is the menu order.
"""

from __future__ import annotations

from collections.abc import Callable

from .llm import cleanup as _llm_cleanup


def _plain(text: str) -> str:
    return text


def _lowercase(text: str) -> str:
    # SF-tech-bro aesthetic: everything lowercase, punctuation untouched.
    return text.lower()


def _uppercase(text: str) -> str:
    return text.upper()


def _clean(text: str) -> str:
    """LLM-powered cleanup: removes fillers, fixes punctuation, keeps meaning."""
    return _llm_cleanup(text)

STYLES: dict[str, Callable[[str], str]] = {
    "plain": _plain,
    "lowercase": _lowercase,
    "uppercase": _uppercase,
    "clean": _clean,
}

DEFAULT_STYLE = "plain"


def apply_style(name: str, text: str) -> str:
    """Apply the named style; unknown names fall back to plain (never raise)."""
    return STYLES.get(name, _plain)(text)
