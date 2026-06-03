"""Menu-bar status indicator (rumps / AppKit).

Runs the AppKit event loop on the main thread and drives the engine on a worker
thread. A timer polls the engine's `state` and updates the menu-bar glyph, so all
AppKit mutations happen on the main thread (cross-thread UI calls are unsafe).
"""

from __future__ import annotations

import threading

import rumps
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

from .app import IDLE, LOADING, RECORDING, TRANSCRIBING, Engine

# Menu-bar glyph per engine state.
TITLES = {
    LOADING: "⏳",
    IDLE: "🎙️",
    RECORDING: "🔴",
    TRANSCRIBING: "✍️",
}

# Dropdown status line per state.
STATUS = {
    LOADING: "Loading model…",
    IDLE: "Ready — double-tap Right Option",
    RECORDING: "Recording… double-tap to stop",
    TRANSCRIBING: "Transcribing…",
}


class MenuBar(rumps.App):
    def __init__(self, engine: Engine) -> None:
        super().__init__("yap", title=TITLES[LOADING], quit_button="Quit")
        self.engine = engine
        self._status = rumps.MenuItem(STATUS[LOADING])  # no callback => non-clickable label
        self.menu = [self._status]

    @rumps.timer(0.15)
    def _refresh(self, _) -> None:  # noqa: ANN001
        st = self.engine.state
        self.title = TITLES.get(st, TITLES[IDLE])
        self._status.title = STATUS.get(st, st)

    def start(self) -> None:
        # Accessory: live in the menu bar only, no dock icon, never steal focus.
        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory
        )
        # Engine owns all MLX work on its own thread (streams are thread-local).
        threading.Thread(target=self.engine.run, daemon=True).start()
        self.engine.start_listener()
        self.run()  # blocks on the AppKit run loop (main thread)
