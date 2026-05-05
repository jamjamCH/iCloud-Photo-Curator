# Security Policy

## Supported Versions

This project is currently in alpha. Only the latest version on the `main` branch
receives security attention.

| Version | Supported |
| --- | --- |
| 0.1.x (main) | Yes |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not open a public GitHub
issue**. Instead, report it privately via
[GitHub Security Advisories](https://github.com/jamjamCH/iCloud-Photo-Curator/security/advisories/new).

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce or a minimal proof-of-concept
- Your suggested fix, if you have one

You will receive a response within 7 days. Please allow reasonable time for a
fix before public disclosure.

## Security Design

| Property | How it is enforced |
| --- | --- |
| No photo deletion | Not implemented; not callable via MCP |
| Passwords not stored in `.env` | Only Apple ID and region are allowed config keys |
| Passwords only in OS Keyring | Login flow uses `icloudpy.utils.store_password_in_keyring` |
| Session cookies stored locally | Isolated under `~/.icloud-photo-curator/session/` |
| Write operations dry-run by default | `dry_run=True` is the default on all write tools |
| Live writes require env flag | `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true` must be set as a real env variable |
| Live writes require two confirmation strings | Both `confirmation` and `risk_acknowledgement` must match exactly |
| No external API calls from MCP server | All image analysis happens in the local AI client |

## Scope

The write adapter uses private iCloud Photos CloudKit endpoints. Apple does not
provide a public API for this workflow. This is an inherent risk of the project
and is documented in [docs/security.md](docs/security.md).

Vulnerabilities in `icloudpy` (the upstream dependency) should be reported to
that project directly.
