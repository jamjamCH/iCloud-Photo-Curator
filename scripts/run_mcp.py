from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _venv_python(root: Path) -> Path | None:
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    server = root / "scripts" / "icloud_photo_curator_mcp.py"
    python = _venv_python(root) or Path(sys.executable)
    env = os.environ.copy()
    env.setdefault("ICLOUD_PHOTO_CURATOR_STATE_DIR", "~/.icloud-photo-curator")
    return subprocess.call([str(python), str(server), *sys.argv[1:]], cwd=str(root), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
