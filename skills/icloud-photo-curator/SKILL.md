---
name: icloud-photo-curator
description: Use when organizing iCloud Photos with the local MCP server. It scans remote albums, reads metadata and GPS fields, fetches small photo versions for Codex-native image review, and stores safe album proposals without deleting or modifying iCloud by default.
---

# iCloud Photo Curator

Use this skill when the user wants to inspect, classify, or organize iCloud Photos by album, GPS metadata, filenames, dates, screenshots/videos, or image understanding performed by Codex in the current chat/plugin context.

## Safety defaults

- Treat the MCP as read-first and proposal-first.
- Do not ask for Apple ID passwords in chat unless the user explicitly chooses that path.
- Prefer environment variables or keyring-backed `icloudpy` authentication.
- Prefer the one-time `try_curator.py login` flow. It writes only safe config to `~/.icloud-photo-curator/.env` and stores the password in Windows Keyring.
- Never store or suggest storing iCloud passwords in `.env`.
- Never delete photos.
- Treat album writes as experimental and gated. Never claim that a live write succeeded unless the MCP tool reports success.
- Never write without first showing a dry-run plan and receiving explicit user approval.
- Use `thumb` or `medium` versions for Codex review; avoid originals unless the user explicitly requests an original download.
- Do not require or suggest an OpenAI API key for the normal workflow.

## Workflow

1. Run `setup_check` to see dependency, `.env`, session, and Keyring status.
2. If Apple ID or Keyring password is missing, ask the user to run `python scripts/try_curator.py login`.
3. Run `curation_workflow_guide` and ask the user which mode they want: scan only, scan and propose, or apply approved proposals.
4. Ask for scope before scanning: source album, batch size, preview size, and whether personal sorting rules should be updated.
5. Run `get_curation_rules`; if the user gives new preferences, call `save_curation_rules`.
6. Run `connect_icloud`; if it requires 2FA, ask the user for the current code and call `validate_2fa_code`.
7. Run `list_albums` to understand existing album names.
8. For scan-only mode, run `scan_album` and summarize without making proposals.
9. For proposal mode, run `prepare_batch_for_codex` with `version="thumb"` or `version="medium"`.
10. Inspect each returned `local_image_path` with Codex's native image understanding.
11. Combine visual understanding with metadata/GPS/existing albums and curation rules.
12. Call `save_codex_proposal` for each decision, including rule matches when useful.
13. Run `review_proposals` and summarize the actions before any write attempt.
14. For write mode, run `write_capabilities`, show a dry-run plan, and apply only approved proposals when the user explicitly confirms the required phrases.

## Album recommendations

Codex should consider:

- Existing album names first.
- Visual content from the cached thumbnail/medium image.
- GPS latitude/longitude if present.
- Asset date and added date.
- Filename patterns such as screenshot names.
- Media type, duration, favorites, hidden flags, captions.

Use conservative confidence. Anything uncertain should become `needs_review`.

## Required user questions

- "Do you want me to only scan, scan and make proposals, or apply already approved proposals?"
- "Which album or scope should I process?"
- "How many photos should I process in this batch?"
- "Should I use `thumb` or `medium` previews?"
- "Do you have personal sorting rules I should follow or update first?"

## Write adapter warning

Creating iCloud Photos albums or adding photos to albums requires private iCloud Photos CloudKit mutations. Do not improvise these mutations against a real library. Implement and test writes only with disposable albums and a tiny set of known assets.

The MCP exposes a narrow experimental write adapter for creating albums and adding photos to albums. It defaults to dry-run and requires `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true`, the exact confirmation phrase, and the exact user responsibility acknowledgement before live writes.

Do not delete photos, remove photos from albums, rename albums, or delete albums. If the user asks for any unsupported destructive action, explain that this plugin does not implement it.
