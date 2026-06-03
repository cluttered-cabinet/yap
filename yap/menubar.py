"""Menu-bar status indicator (rumps / AppKit).

Runs the AppKit event loop on the main thread and drives the engine on a worker
thread. A timer polls the engine's `state` and updates the menu-bar glyph, so all
AppKit mutations happen on the main thread (cross-thread UI calls are unsafe).

Also owns the Accessibility-trust gate: when launched as a .app there is no
terminal, so an untrusted launch shows a ⚠️ menu with a button to open the
Accessibility settings instead of printing to stdout.
"""

from __future__ import annotations

import os
import subprocess
import threading

import rumps
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

from .app import IDLE, LOADING, RECORDING, TRANSCRIBING, Engine
from .perms import is_trusted, request_trust

_SETTINGS_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"

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
    IDLE: "Ready — hold or double-tap Right Option",
    RECORDING: "Recording… release or double-tap to stop",
    TRANSCRIBING: "Transcribing…",
}


class MenuBar(rumps.App):
    def __init__(self, engine: Engine) -> None:
        super().__init__("yap", title=TITLES[LOADING], quit_button="Quit")
        self.engine = engine
        self._trusted = False
        self._status = rumps.MenuItem(STATUS[LOADING])  # no callback => non-clickable label
        self.menu = [self._status]

    @rumps.timer(0.15)
    def _refresh(self, _) -> None:  # noqa: ANN001
        if not self._trusted:
            return  # ⚠️ permission UI owns the title until granted + relaunched
        st = self.engine.state
        self.title = TITLES.get(st, TITLES[IDLE])
        self._status.title = STATUS.get(st, st)

    def _open_accessibility(self, _) -> None:  # noqa: ANN001
        request_trust()
        subprocess.run(["open", _SETTINGS_URL], check=False)

    def _relaunch(self, _) -> None:  # noqa: ANN001
        # In-process trust is cached, so a fresh launch is required to pick it up.
        app = os.environ.get("YAP_APP")
        if app:
            subprocess.Popen(["open", "-n", app])
            rumps.quit_application()

    def start(self) -> None:
        # Accessory: live in the menu bar only, no dock icon, never steal focus.
        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory
        )
        self._trusted = is_trusted()
        if not self._trusted:
            # No global key capture / typing without trust. Show how to fix it.
            request_trust()  # adds this app to the Accessibility list
            self.title = "⚠️"
            self._status.title = "Accessibility required — grant, then relaunch yap"
            self.menu = [
                self._status,
                rumps.MenuItem(
                    "Open Accessibility Settings…", callback=self._open_accessibility
                ),
                rumps.MenuItem("Relaunch yap", callback=self._relaunch),
            ]
            self.run()
            return
        # Engine owns all MLX work on its own thread (streams are thread-local).
        threading.Thread(target=self.engine.run, daemon=True).start()
        self.engine.start_listener()
        self.run()  # blocks on the AppKit run loop (main thread)
