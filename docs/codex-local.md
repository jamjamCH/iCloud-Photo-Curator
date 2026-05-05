# Codex Desktop Local Installation

This guide installs **iCloud Photo Curator** as a local Codex plugin.

## Folder Placement

Place the unzipped folder here:

| Platform | Folder |
| --- | --- |
| Windows | `C:\Users\<you>\plugins\icloud-photo-curator` |
| macOS | `~/plugins/icloud-photo-curator` |
| Linux | `~/plugins/icloud-photo-curator` |

If the extracted folder is named `icloud-photo-curator-main`, rename it to `icloud-photo-curator`.

## Bootstrap

From the plugin folder:

```powershell
python scripts/bootstrap.py
python scripts/try_curator.py setup
python scripts/try_curator.py login
```

## Codex Marketplace Entry

Create or update:

| Platform | Marketplace file |
| --- | --- |
| Windows | `C:\Users\<you>\.agents\plugins\marketplace.json` |
| macOS | `~/.agents/plugins/marketplace.json` |
| Linux | `~/.agents/plugins/marketplace.json` |

Minimal marketplace file:

```json
{
  "name": "local",
  "interface": {
    "displayName": "Local Plugins"
  },
  "plugins": [
    {
      "name": "icloud-photo-curator",
      "source": {
        "source": "local",
        "path": "./plugins/icloud-photo-curator"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_USE"
      },
      "category": "Productivity"
    }
  ]
}
```

If you already have a marketplace file, merge only the plugin entry into the existing `plugins` array.

## Activate In Codex

1. Restart Codex Desktop.
2. Open the plugin list.
3. Install or enable **iCloud Photo Curator**.
4. Start a new Codex session and ask it to connect to iCloud.

## Expected Commands

After setup, Codex should be able to call MCP tools such as:

| Tool | Expected use |
| --- | --- |
| `setup_check` | Confirm `.env`, Keyring, session, and dependencies |
| `connect_icloud` | Open a session without passing username/password |
| `list_albums` | Read existing albums |
| `prepare_batch_for_codex` | Cache small previews for Codex review |
| `save_codex_proposal` | Save local proposals only |
| `write_capabilities` | Check whether experimental writes are enabled |
| `create_album` | Dry-run or create an album after explicit approval |
| `add_photo_to_album` | Dry-run or add one photo after explicit approval |
| `apply_proposals` | Dry-run or apply approved local proposals |

## Safety

Codex should start with `curation_workflow_guide`, ask whether the user wants scan-only, proposals, or approved writes, and run write tools in dry-run mode first.

Live iCloud album writes are experimental. They require `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true` plus the exact confirmation and risk acknowledgement returned by `write_capabilities`. The plugin never implements photo deletion.
