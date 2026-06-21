# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Experimental Claude Desktop extension packaging: `manifest.json`,
  `scripts/build_mcpb.py` to build a `.mcpb` bundle, and
  `scripts/mcpb_launch.py`, which bootstraps dependencies into a private venv
  on first launch so the bundle stays small and cross-platform.
- Release workflow (`.github/workflows/release.yml`) that builds the `.mcpb`
  bundle and attaches it to the GitHub Release when one is published.

### Changed
- Rewrote the Claude Desktop and Codex setup guides (EN + DE) and the README
  intros/quick start to be beginner-friendly: plain-language "what it does",
  prerequisites, expected results per step, correct shell blocks, an example
  prompt, and a troubleshooting section.

## [0.2.0] - 2026-06-21

### Added
- **Client-native vision via MCP image blocks.** `prepare_photo_for_codex` and
  `prepare_batch_for_codex` now return the actual photos as MCP image blocks
  (interleaved with `asset_id` markers), so the connected vision model
  (Codex/GPT or Claude Desktop) sees the pixels and sorts by visible content
  (food → Food, documents → Documents, …). No external vision API is used.
- New `get_photo_image` tool that returns one photo as an MCP image block for
  precise, content-based review of a single asset.
- **Offline location albums.** GPS coordinates are resolved to
  city/state/country with the offline `reverse_geocode` dataset (no network
  call) and exposed as `metadata.location`; travel photos are proposed for
  place-based albums instead of a generic placeholder.
- Optional `[geo]` extra and `reverse_geocode` in `requirements.txt`;
  `setup_check` reports `reverse_geocode_installed` and a `location_albums`
  status.
- GitHub Actions CI running `ruff` and `pytest` on Python 3.10–3.12.
- Tests for the geocoding helper and the location-aware proposal heuristic.

### Changed
- `setup_check` now reports `vision_mode: client_native_mcp_image` and a
  vision/geocoder status instead of the old `codex_native_ai_mode` flag.
- The CLI `prepare` command prints JSON (`embed_images=False`) instead of
  embedding non-serializable image objects.
- Documentation (EN + DE) updated across README, security, codex-local,
  claude-desktop, CLI references, and the skill to describe the real vision and
  location flow.

### Fixed
- Corrected misleading docstrings: `analyze_photo` and `curate_batch` are now
  honestly documented as metadata-only fallbacks that do not call a vision
  model.
- `try_curator.py` no longer crashes when the Apple ID is empty; `_connect`
  returns a structured error dict instead of `None`.
- Replaced "Windows Keyring" with "OS Keyring" in CLI help text, the `.env`
  comment, and the skill, since the keyring is cross-platform.
- Documented the previously missing `connect` and `curate` CLI subcommands.
- Resolved all 42 `ruff` violations (line length, unused imports, import
  ordering); lint is now clean.

## [0.1.0] - 2025

### Added
- Initial release: local MCP server and Codex plugin for iCloud Photos
  curation with album scanning, metadata reading, local proposal review, and an
  experimental gated album write adapter (dry-run by default, never deletes
  photos).

[0.2.0]: https://github.com/jamjamCH/iCloud-Photo-Curator/releases/tag/v0.2.0
[0.1.0]: https://github.com/jamjamCH/iCloud-Photo-Curator/releases/tag/v0.1.0
