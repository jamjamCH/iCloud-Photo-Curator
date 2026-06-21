# iCloud Photo Curator

[![status](https://img.shields.io/badge/status-alpha-0B6E69)](#development-status)
[![python](https://img.shields.io/badge/python-3.10%2B-173A5E)](https://www.python.org/)
[![mcp](https://img.shields.io/badge/MCP-stdio-2F6F9F)](https://modelcontextprotocol.io/)
[![writes](https://img.shields.io/badge/iCloud_writes-experimental_gated-8A6D1D)](#safety-model)
[![no deletions](https://img.shields.io/badge/photo_deletion-never-2D6A27)](#safety-model)
[![dry run](https://img.shields.io/badge/writes-dry--run_by_default-5A3E8A)](#safety-model)
[![tests](https://img.shields.io/badge/tests-pytest-4B8BBE)](tests/)
[![license](https://img.shields.io/badge/license-MIT-3B7C3A)](LICENSE)

*Deutsch: [README.de.md](README.de.md)*

**iCloud Photo Curator** is a local Codex plugin and MCP server for safe, AI-assisted iCloud Photos curation. It reads remote iCloud Photos metadata, lists albums, and returns small thumbnails or medium previews **as MCP image blocks** so the connected vision model (Codex/GPT or Claude) actually *sees* each photo and sorts it by visual content — food into a Food album, documents into Documents, and so on. GPS coordinates are resolved to a city/country **offline** so travel photos can be grouped by place. No external vision API is called: the connected model is the vision model.

It does **not** delete photos. Album creation and adding photos to albums are available only through an **experimental gated write mode** that defaults to dry-run and requires explicit user approval before any live iCloud change.

## Overview

| Area | Current behavior |
| --- | --- |
| iCloud access | Uses `icloudpy` and iCloud web/private CloudKit endpoints |
| AI review | The MCP returns photos as image blocks; the connected model (Codex/GPT or Claude) sees the pixels and classifies content |
| Location | GPS is resolved offline to city/state/country via `reverse_geocode` for place-based albums |
| Downloads | Small `thumb` or `medium` versions by default, not originals |
| Credentials | Apple ID in local `.env`, password in OS Keyring only |
| Writes | Experimental, dry-run by default; live writes require env flag and exact confirmations |
| Status | Alpha prototype for careful local testing |

## Operating Modes

The AI client should ask which mode the user wants before processing a library.

| Mode | What happens | iCloud writes |
| --- | --- | --- |
| Scan only | Read albums and metadata, summarize structure | No |
| Scan and propose | Cache small previews, inspect them, save local proposals | No |
| Apply approved proposals | Apply reviewed proposals through the gated write adapter | Dry-run by default; live writes require explicit approval |

The MCP exposes `curation_workflow_guide` so clients can retrieve these required questions instead of guessing the workflow.

## How Vision And Location Sorting Work

Sorting by *what is actually in the picture* needs a vision model. This plugin does **not** call an external vision API. Instead it uses the model you are already talking to:

1. `prepare_batch_for_codex` (or `get_photo_image` for a single asset) downloads a small `thumb`/`medium` version and returns it as a real **MCP image block**, preceded by a text marker with its `asset_id`.
2. Codex/GPT or Claude Desktop receives the actual pixels and classifies the content (food, document, landscape, portrait, receipt, screenshot, …).
3. For GPS-tagged photos the server resolves the coordinates to a `city`, `state`, and `country` using the offline `reverse_geocode` dataset (no network call), so travel photos can be grouped by place.
4. The model combines vision + location + metadata + your personal rules and calls `save_codex_proposal` for each decision.

So a food photo lands in **Food**, and a vacation photo taken in Paris is proposed for a **Paris** album. The older `analyze_photo` / `curate_batch` tools are a metadata-only fallback (filename, media type, location) and do **not** look at pixels.

Location albums require the optional offline geocoder. It is included in `requirements.txt`, or install it separately:

```text
pip install reverse_geocode
```

`setup_check` reports `reverse_geocode_installed` and a `location_albums` status.

## Recommended Folder Location

When downloading the GitHub ZIP, extract it and place the unzipped folder here:

| Platform | Recommended folder |
| --- | --- |
| Windows | `C:\Users\<you>\plugins\icloud-photo-curator` |
| macOS | `~/plugins/icloud-photo-curator` |
| Linux | `~/plugins/icloud-photo-curator` |

If GitHub extracts the folder as `icloud-photo-curator-main`, rename it to `icloud-photo-curator`.

## Quick Start

From the plugin folder:

```powershell
python scripts/bootstrap.py
python scripts/try_curator.py login
python scripts/try_curator.py albums
python scripts/try_curator.py prepare --album "All Photos" --limit 10 --version thumb
```

On Windows, after bootstrapping, you can also use the virtual environment directly:

```powershell
.\.venv\Scripts\python.exe .\scripts\try_curator.py setup
```

On macOS or Linux:

```bash
./.venv/bin/python scripts/try_curator.py setup
```

## Local Config

The local config file is created at:

```text
~/.icloud-photo-curator/.env
```

Supported keys:

```text
ICLOUD_PHOTO_CURATOR_APPLE_ID="you@example.com"
ICLOUD_PHOTO_CURATOR_REGION="global"
ICLOUD_PHOTO_CURATOR_STATE_DIR="~/.icloud-photo-curator"
```

Real environment variables override values from `.env`.

**Do not store the iCloud password in `.env`.** The `login` command stores the password in the operating system Keyring through `icloudpy.utils.store_password_in_keyring`.

The `.env` file is intentionally limited to safe config keys. Experimental write flags must be set as real environment variables, not stored in `.env`.

## Personal Sorting Rules

Every user sorts photos differently. The plugin keeps local rules here:

```text
~/.icloud-photo-curator/rules.md
```

The AI client should read these rules before making proposals. Users can edit the file manually or use:

```powershell
python scripts/try_curator.py rules
python scripts/try_curator.py rules --add "Prefer existing travel albums for GPS-tagged vacation photos."
```

Example rules:

| Rule type | Example |
| --- | --- |
| Album preference | Prefer existing albums over creating near-duplicates |
| Naming | Use short album names in title case |
| Privacy | Do not infer real names from faces |
| Uncertainty | Mark uncertain photos as `needs_review` |

## Documentation

| Document | Description |
| --- | --- |
| [Codex Desktop setup](docs/codex-local.md) | Connect the plugin to Codex Desktop |
| [Claude Desktop setup](docs/claude-desktop.md) | Connect the plugin to Claude Desktop |
| [CLI reference](docs/cli.md) | Manual testing and scripting without a GUI client |
| [Security model](docs/security.md) | Credential handling, write guards, and privacy notes |

## MCP Tools

| Tool | Purpose | iCloud write access |
| --- | --- | --- |
| `setup_check` | Shows config, Keyring, session, and dependency status | No |
| `curation_workflow_guide` | Returns required workflow questions and available operating modes | No |
| `get_curation_rules` | Reads the user's local album sorting rules | No |
| `save_curation_rules` | Creates or updates local sorting rules | No |
| `connect_icloud` | Starts an iCloud session from args, env, `.env`, or Keyring | No |
| `validate_2fa_code` | Submits Apple 2FA and trusts the session when possible | No |
| `list_albums` | Lists iCloud Photos albums | No |
| `scan_album` | Reads metadata without downloading originals | No |
| `download_photo_version` | Caches one small version locally | No |
| `get_photo_image` | Returns one photo as an MCP image block for client-native vision | No |
| `prepare_photo_for_codex` | Returns one photo (image block) + metadata/location for review | No |
| `prepare_batch_for_codex` | Returns a small batch as image blocks + metadata/location for review | No |
| `analyze_photo` | Metadata-only fallback (no vision model); returns album recommendations | No |
| `curate_batch` | Metadata-only fallback batch; stores proposed album actions | No |
| `save_codex_proposal` | Stores a local album decision | No |
| `review_proposals` | Reviews saved proposals | No |
| `mark_proposals_reviewed` | Approves or rejects proposals locally | No |
| `export_proposals` | Exports stored proposals to JSON for backup or manual review | No |
| `write_capabilities` | Shows supported write operations and required confirmations | No |
| `create_album` | Dry-run or create one iCloud Photos album | Experimental gated |
| `add_photo_to_album` | Dry-run or add one photo to one album | Experimental gated |
| `apply_proposals` | Dry-run or apply approved local proposals | Experimental gated |

## Safety Model

The current release is intentionally conservative:

| Rule | Status |
| --- | --- |
| No photo deletion | Enforced |
| Album writes dry-run by default | Enforced |
| Live album writes require env flag and exact confirmations | Enforced |
| No original downloads by default | Enforced by workflow |
| Password not written to `.env` | Enforced by login flow |
| Trusted sessions isolated under state dir | Enforced |

## Write Access And Responsibility

Write access is intentionally narrow: the plugin can create albums and add photos to albums. It cannot delete photos, remove photos from albums, rename albums, or delete albums.

Live writes use private iCloud Photos CloudKit behavior. Apple does not provide a public iCloud Photos write API for this workflow, so users must test with disposable albums and small batches before applying changes to a real library.

Users are responsible for every write action they approve. Codex or Claude should always show the dry-run plan first and ask for explicit approval before live writes.

| Write safeguard | Reason |
| --- | --- |
| Dry-run first | Shows exactly what would change |
| Explicit user approval | Prevents silent album changes |
| Small batch default | Limits accidental large-scale mistakes |
| Disposable album validation | Confirms private API behavior before real use |
| User responsibility acknowledgement | Makes risk and ownership clear |

To enable live writes outside dry-run mode, set this as a real environment variable, not in `~/.icloud-photo-curator/.env`:

```text
ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true
```

The MCP will still require these exact strings before writing:

| Required field | Exact value |
| --- | --- |
| `confirmation` | `I understand this will change my iCloud Photos albums` |
| `risk_acknowledgement` | `I understand iCloud album writes are experimental and I am responsible for the changes` |

## Development Status

This is an alpha local-first integration. Read access, proposal workflows, and a narrow experimental write adapter are available. The write adapter must be validated with disposable albums because it relies on private iCloud Photos CloudKit mutations.

## Not Affiliated With Apple

This project is not affiliated with or endorsed by Apple. iCloud and iCloud Photos are trademarks of Apple Inc.
