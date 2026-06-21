"""Launcher for the Claude Desktop (.mcpb) bundle.

Claude Desktop starts this with the system ``python`` (declared in
manifest.json). The MCP server itself needs third-party dependencies
(``mcp``, ``icloudpy``, ``keyring``, ``reverse_geocode``), which are not part
of the system interpreter. To keep the bundle small and cross-platform this
launcher ensures a private virtual environment with those dependencies and then
re-executes the real server with it.

First launch creates the venv and pip-installs ``requirements.txt`` (this needs
network access and may take a moment). Later launches reuse the venv and start
instantly. Set ``ICLOUD_PHOTO_CURATOR_MCPB_DRYRUN=1`` to print the resolved
paths and exit without installing or starting the server.
"""
from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

EXT_DIR = Path(__file__).resolve().parents[1]
SERVER = EXT_DIR / "scripts" / "icloud_photo_curator_mcp.py"
REQUIREMENTS = EXT_DIR / "requirements.txt"


def _state_dir() -> Path:
    raw = os.environ.get("ICLOUD_PHOTO_CURATOR_STATE_DIR", "~/.icloud-photo-curator")
    path = Path(os.path.expanduser(raw))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _ensure_venv() -> Path:
    venv_dir = _state_dir() / "mcpb-venv"
    python = _venv_python(venv_dir)
    marker = venv_dir / ".deps-installed"
    if not python.exists():
        print(f"[icloud-photo-curator] Creating virtual environment at {venv_dir}", file=sys.stderr)
        venv.create(venv_dir, with_pip=True)
    if not marker.exists():
        print(
            "[icloud-photo-curator] Installing dependencies (first launch only)...",
            file=sys.stderr,
        )
        subprocess.check_call(
            [str(python), "-m", "pip", "install", "-q", "-r", str(REQUIREMENTS)]
        )
        marker.write_text("ok", encoding="utf-8")
    return python


def _server_python() -> Path:
    """Return an interpreter that can import the server's dependencies."""
    try:
        import mcp  # noqa: F401  (just a capability probe)

        return Path(sys.executable)
    except ModuleNotFoundError:
        return _ensure_venv()


def main() -> int:
    python = _server_python()
    if os.environ.get("ICLOUD_PHOTO_CURATOR_MCPB_DRYRUN") == "1":
        print(f"server={SERVER}")
        print(f"python={python}")
        return 0
    os.execv(str(python), [str(python), str(SERVER), *sys.argv[1:]])
    return 0  # unreachable; execv replaces the process


if __name__ == "__main__":
    raise SystemExit(main())
