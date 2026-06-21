"""Build the Claude Desktop extension bundle (.mcpb).

A .mcpb file is a ZIP archive with ``manifest.json`` at its root. This script
validates the manifest and packages the source the server needs into
``dist/icloud-photo-curator-<version>.mcpb``. Dependencies are not bundled;
``scripts/mcpb_launch.py`` installs them into a private venv on first launch.

Run:  python scripts/build_mcpb.py
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

# Files and directories included in the bundle. Directories are added
# recursively; caches and the local venv are skipped.
INCLUDE = [
    "manifest.json",
    "requirements.txt",
    "README.md",
    "LICENSE",
    "scripts",
    "skills",
    "assets",
]
SKIP_DIRS = {"__pycache__", ".venv", "mcpb-venv", ".pytest_cache", ".ruff_cache"}
REQUIRED_MANIFEST_KEYS = {"manifest_version", "name", "version", "server"}


def _load_manifest() -> dict:
    manifest_path = ROOT / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("manifest.json not found at repository root.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"manifest.json is not valid JSON: {exc}") from exc
    missing = REQUIRED_MANIFEST_KEYS - manifest.keys()
    if missing:
        raise SystemExit(f"manifest.json is missing required keys: {sorted(missing)}")
    entry = manifest.get("server", {}).get("entry_point")
    if entry and not (ROOT / entry).exists():
        raise SystemExit(f"server.entry_point '{entry}' does not exist.")
    return manifest


def _iter_files(name: str):
    target = ROOT / name
    if target.is_file():
        yield target
        return
    for path in sorted(target.rglob("*")):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        yield path


def main() -> int:
    manifest = _load_manifest()
    version = manifest["version"]
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"icloud-photo-curator-{version}.mcpb"

    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in INCLUDE:
            source = ROOT / name
            if not source.exists():
                print(f"  skip (missing): {name}", file=sys.stderr)
                continue
            for path in _iter_files(name):
                archive.write(path, path.relative_to(ROOT).as_posix())
                count += 1

    size_kb = out.stat().st_size / 1024
    print(f"Built {out.relative_to(ROOT)} ({count} files, {size_kb:.0f} KB)")
    print("Dependencies are installed into a private venv on first launch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
