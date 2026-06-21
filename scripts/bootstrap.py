from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if sys.platform.startswith("win") else "bin/python")


def main() -> int:
    if not VENV.exists():
        print(f"Creating virtual environment at {VENV}")
        venv.create(VENV, with_pip=True)
    print("Installing Python dependencies")
    return subprocess.call(
        [str(PYTHON), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")]
    )


if __name__ == "__main__":
    raise SystemExit(main())
