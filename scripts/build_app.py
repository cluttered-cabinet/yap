"""Build a minimal `yap.app` wrapper so yap runs in the background, no terminal.

The bundle's executable is a tiny shell script that execs this project's uv venv
Python on main.py. It is therefore NOT self-contained: it depends on this
checkout and its `.venv` staying where they are. Re-run this script after moving
the project or recreating the venv.

Why a wrapper instead of py2app: bundling MLX/Metal, numba, and llvmlite into a
relocatable app is fragile and large; for a personal background tool a wrapper is
robust and instant. macOS attributes TCC (Accessibility/Mic/Input Monitoring) to
the bundle identity, so permissions stick to "yap" rather than your terminal.
"""

from __future__ import annotations

import plistlib
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PY = ROOT / ".venv" / "bin" / "python"
MAIN = ROOT / "main.py"
APP = ROOT / "yap.app"

INFO = {
    "CFBundleName": "yap",
    "CFBundleDisplayName": "yap",
    "CFBundleIdentifier": "com.cluttered-cabinet.yap",
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

    macos = APP / "Contents" / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)

    with (APP / "Contents" / "Info.plist").open("wb") as f:
        plistlib.dump(INFO, f)

    launcher = macos / "yap"
    launcher.write_text(
        "#!/bin/bash\n"
        f'cd "{ROOT}"\n'
        f'exec "{VENV_PY}" "{MAIN}" >> "$HOME/Library/Logs/yap.log" 2>&1\n'
    )
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Built {APP}")
    print("\nNext:")
    print(f"  open '{APP}'   # launch now (first run prompts for permissions)")
    print("  Autostart: System Settings > General > Login Items > '+' and add yap.app")
    print("  Logs: ~/Library/Logs/yap.log")


if __name__ == "__main__":
    main()
