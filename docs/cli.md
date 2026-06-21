# Manual CLI Testing

The CLI helper is useful before connecting the MCP server to Codex or Claude Desktop.

## Bootstrap

```powershell
python scripts/bootstrap.py
```

## Login

```powershell
python scripts/try_curator.py login
```

This creates or updates `~/.icloud-photo-curator/.env`, stores the iCloud password in OS Keyring, and validates 2FA when Apple requests it.

## Commands

| Command | Purpose |
| --- | --- |
| `python scripts/try_curator.py setup` | Check dependencies, config, session directory, Keyring, and geocoder status |
| `python scripts/try_curator.py login` | Configure Apple ID, Keyring password, and trusted session |
| `python scripts/try_curator.py connect` | Test iCloud login and 2FA state without scanning |
| `python scripts/try_curator.py albums` | List albums after login |
| `python scripts/try_curator.py scan --album "All Photos" --limit 5` | Read metadata only (includes resolved GPS location) |
| `python scripts/try_curator.py prepare --album "All Photos" --limit 3 --version thumb` | Cache small previews + metadata/location for AI-client review |
| `python scripts/try_curator.py curate --album "All Photos" --limit 3` | Legacy metadata-only batch proposal helper (no vision) |
| `python scripts/try_curator.py review` | Review locally saved proposals |
| `python scripts/try_curator.py rules` | Show personal sorting rules |
| `python scripts/try_curator.py rules --add "Prefer existing albums."` | Append a sorting rule |
| `python scripts/try_curator.py write-capabilities` | Show experimental write safeguards |
| `python scripts/try_curator.py create-album --album "Food"` | Dry-run album creation |
| `python scripts/try_curator.py add-photo --album "Food" --asset-id <id>` | Dry-run adding one photo |
| `python scripts/try_curator.py apply-proposals <proposal-id>` | Dry-run approved proposal application |

## Experimental Writes

Write commands default to dry-run. Live writes require `--execute`, the real environment variable `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true` outside `.env`, and the exact `--confirmation` and `--risk-acknowledgement` strings returned by:

```powershell
python scripts/try_curator.py write-capabilities
```

Test live writes only with disposable albums and tiny batches first. The CLI does not implement deleting photos.

## 2FA Retry

If Apple asks for 2FA outside the login flow:

```powershell
python scripts/try_curator.py albums --two-factor-code 123456
```

## Output Safety

The CLI never prints passwords. `setup` reports only whether a Keyring password appears to be available.
