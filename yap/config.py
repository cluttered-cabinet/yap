"""Tiny JSON config persisted to ~/.config/yap/config.json.

Used to remember preferences (e.g. the chosen output style) across launches.
Reads never raise: a missing or corrupt file yields an empty config.
"""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path.home() / ".config" / "yap" / "config.json"


def load() -> dict:
    try:
        return json.loads(PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, indent=2))


def get(key: str, default=None):  # noqa: ANN001, ANN201
    return load().get(key, default)


def set(key: str, value) -> None:  # noqa: ANN001, A001
    data = load()
    data[key] = value
    save(data)
