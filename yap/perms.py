"""macOS Accessibility trust checks.

Global keyboard capture (pynput's CGEventTap) and synthesized typing both require
the host process to be *trusted for Accessibility*. Without trust, the event tap
only receives events for the focused app -- so the shortcut appears to work only
while the terminal is frontmost. With trust, the same tap is system-wide.
"""

from __future__ import annotations

import ApplicationServices as _AX


def is_trusted() -> bool:
    """True if this process may observe global input and post events."""
    return bool(_AX.AXIsProcessTrusted())


def request_trust() -> bool:
    """Show the macOS Accessibility prompt, adding this process to the list.

    Returns the trust state at call time (typically False on first run -- the
    user must toggle the entry on and relaunch for it to take effect).
    """
    options = {_AX.kAXTrustedCheckOptionPrompt: True}
    return bool(_AX.AXIsProcessTrustedWithOptions(options))
