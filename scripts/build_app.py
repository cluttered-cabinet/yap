"""Build a `yap.app` wrapper so yap runs in the background, no terminal.

The bundle's executable is a tiny shell script that execs this project's uv venv
Python on main.py. It is NOT self-contained: it depends on this checkout and its
`.venv` staying where they are. Re-run after moving the project or recreating the
venv.

Accessibility note: the trusted process is the external venv interpreter, reached
via the bundle. For TCC to attribute its trust to "yap" the bundle MUST have a
stable code identity, so we ad-hoc codesign it. Without a signature the grant is
keyed to the bundle's path and breaks the moment you move the app (e.g. into
/Applications) -- which looks like "stuck on Accessibility".

Usage:
    uv run scripts/build_app.py [DEST_DIR]   # DEST_DIR defaults to project root
    uv run scripts/build_app.py /Applications
"""

from __future__ import annotations

import plistlib
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PY = ROOT / ".venv" / "bin" / "python"
MAIN = ROOT / "main.py"
BUNDLE_ID = "com.cluttered-cabinet.yap"

INFO = {
    "CFBundleName": "yap",
    "CFBundleDisplayName": "yap",
    "CFBundleIdentifier": BUNDLE_ID,
    "CFBundleExecutable": "yap",
    "CFBundlePackageType": "APPL",
    "CFBundleShortVersionString": "0.1.0",
    "CFBundleVersion": "0.1.0",
    "LSUIElement": True,  # menu-bar only; no Dock icon
    "LSMinimumSystemVersion": "14.0",
    "NSMicrophoneUsageDescription": "yap transcribes your microphone for dictation.",
}


def main() -> None:
    if not VENV_PY.exists():
        raise SystemExit(f"venv python not found at {VENV_PY}; run `uv sync` first")

    dest = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else ROOT
    app = dest / "yap.app"
    macos = app / "Contents" / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)

    with (app / "Contents" / "Info.plist").open("wb") as f:
        plistlib.dump(INFO, f)

    launcher = macos / "yap"
    launcher.write_text(
        "#!/bin/bash\n"
        # Absolute path of this .app, derived at runtime so relaunch works
        # regardless of where the bundle was moved.
        'export YAP_APP="$(cd "$(dirname "$0")/../.." && pwd)"\n'
        f'cd "{ROOT}"\n'
        f'exec "{VENV_PY}" "{MAIN}" >> "$HOME/Library/Logs/yap.log" 2>&1\n'
    )
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Ad-hoc sign so the bundle has a stable identity (survives moving the app).
    subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True)

    print(f"Built and ad-hoc signed {app}")
    print("\nIf you previously tried to grant an unsigned build, clear the stale grants:")
    print(f"  tccutil reset Accessibility {BUNDLE_ID}")
    print(f"  tccutil reset ListenEvent {BUNDLE_ID}")
    print(f"  tccutil reset Microphone {BUNDLE_ID}")
    print("\nThen:")
    print(f"  open '{app}'   # launch; enable yap in Accessibility + Input Monitoring")
    print("  Click 'Relaunch yap' in the menu after enabling (or quit + reopen).")
    print("  Autostart: System Settings > General > Login Items > '+' and add yap.app")
    print("  Logs: ~/Library/Logs/yap.log")


if __name__ == "__main__":
    main()
