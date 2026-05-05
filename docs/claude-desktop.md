# Claude Desktop Local Installation

This project can run as a local stdio MCP server in Claude Desktop.

Anthropic currently documents two local paths for Claude Desktop integrations: Desktop Extensions for packaged `.mcpb` installs and local MCP servers for direct development/testing. This repository currently ships a local stdio MCP server; packaging as `.mcpb` can be added later.

## Folder Placement

Place the unzipped folder here:

| Platform | Folder |
| --- | --- |
| Windows | `C:\Users\<you>\plugins\icloud-photo-curator` |
| macOS | `~/plugins/icloud-photo-curator` |
| Linux | `~/plugins/icloud-photo-curator` |

## Bootstrap And Login

From the plugin folder:

```powershell
python scripts/bootstrap.py
python scripts/try_curator.py login
```

## Claude Desktop Config

Edit the Claude Desktop MCP configuration file for your platform.

| Platform | Common config path |
| --- | --- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Use absolute paths. Windows paths in JSON need escaped backslashes.

### Windows Example

```json
{
  "mcpServers": {
    "icloud-photo-curator": {
      "command": "C:\\Users\\YOUR_NAME\\plugins\\icloud-photo-curator\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\YOUR_NAME\\plugins\\icloud-photo-curator\\scripts\\icloud_photo_curator_mcp.py"
      ],
      "env": {
        "ICLOUD_PHOTO_CURATOR_STATE_DIR": "C:\\Users\\YOUR_NAME\\.icloud-photo-curator"
      }
    }
  }
}
```

### macOS Or Linux Example

```json
{
  "mcpServers": {
    "icloud-photo-curator": {
      "command": "/Users/YOUR_NAME/plugins/icloud-photo-curator/.venv/bin/python",
      "args": [
        "/Users/YOUR_NAME/plugins/icloud-photo-curator/scripts/icloud_photo_curator_mcp.py"
      ],
      "env": {
        "ICLOUD_PHOTO_CURATOR_STATE_DIR": "/Users/YOUR_NAME/.icloud-photo-curator"
      }
    }
  }
}
```

For Linux, replace `/Users/YOUR_NAME` with `/home/YOUR_NAME`.

## Restart And Verify

1. Restart Claude Desktop.
2. Open the connector or developer status view.
3. Confirm that `icloud-photo-curator` is connected.
4. Ask Claude to run `setup_check` or list your iCloud albums.

## Notes

| Topic | Detail |
| --- | --- |
| Passwords | Stored in OS Keyring by `try_curator.py login`, not in Claude config |
| 2FA | If a session expires, run `try_curator.py login` again or pass a fresh code through the MCP tool |
| Writes | Experimental album writes are dry-run by default and require explicit env flag plus confirmations |
| Packaging | `.mcpb` desktop extension packaging is a future release step |

For write workflows, ask Claude to call `write_capabilities` first, show the dry-run plan, and only then apply approved proposals if you intentionally enabled experimental writes. The plugin does not implement photo deletion.
