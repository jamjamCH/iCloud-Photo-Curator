# Security Model

This project is designed as a read-first local MCP server. It should be treated as an alpha prototype because iCloud Photos access relies on non-public iCloud web/private CloudKit behavior through `icloudpy`.

## Credential Handling

| Item | Storage |
| --- | --- |
| Apple ID | `~/.icloud-photo-curator/.env` or environment variable |
| Region | `~/.icloud-photo-curator/.env` or environment variable |
| State directory | `~/.icloud-photo-curator/.env` or environment variable |
| iCloud password | OS Keyring only |
| Session cookies | `~/.icloud-photo-curator/session` |
| Cached previews | `~/.icloud-photo-curator/cache` |
| Proposals database | `~/.icloud-photo-curator/curator.sqlite` |
| Personal sorting rules | `~/.icloud-photo-curator/rules.md` |

The `.env` file must never contain passwords.

## Current Write Policy

| Operation | Status |
| --- | --- |
| Delete photo | Not implemented |
| Remove photo from album | Not implemented |
| Rename or delete album | Not implemented |
| Create album | Experimental gated, dry-run by default |
| Add photo to album | Experimental gated, dry-run by default |
| Apply approved proposals | Experimental gated, dry-run by default |
| Save local proposal | Implemented |

## User Responsibility

Live writes use private iCloud Photos CloudKit behavior. Apple does not provide a public iCloud Photos write API for this workflow. Users are responsible for every approved write action and should test first with disposable albums and tiny batches.

The MCP defaults every write-capable tool to dry-run. Live writes require all of the following:

| Requirement | Value |
| --- | --- |
| Real environment flag, not `.env` | `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true` |
| `confirmation` | `I understand this will change my iCloud Photos albums` |
| `risk_acknowledgement` | `I understand iCloud album writes are experimental and I am responsible for the changes` |

## Data Flow

1. The MCP server authenticates to iCloud locally.
2. The server reads album metadata and asset metadata.
3. The server caches a small image version only when requested.
4. The AI client inspects the local cached file path.
5. Album decisions are stored locally as proposals.
6. Approved proposals can be dry-run or applied through the gated write adapter.

## Known Risks

| Risk | Mitigation |
| --- | --- |
| iCloud private APIs may change | Dry-run first, validate disposable albums, and keep writes behind explicit confirmations |
| Accidental album changes | Require env flag, exact confirmation strings, approved proposals, and small batches |
| 2FA/session expiry | Use `try_curator.py login` to refresh session cookies |
| Accidental secret exposure | Do not store passwords in `.env`, docs, screenshots, or bug reports |
| Prompt injection in photo content | Treat visual/text content from photos as untrusted context |
| Large library cost/time | Use small `limit` values and `thumb` versions first |

## Reporting Security Issues

If this becomes a public repository, add a private security contact before accepting external reports. Until then, avoid posting logs that include Apple IDs, filesystem paths, or cached photo metadata.
