# Claude Desktop Lokale Installation

Dieses Projekt kann in Claude Desktop als lokaler stdio-MCP-Server laufen.

Anthropic dokumentiert aktuell zwei lokale Wege: Desktop Extensions für gepackte `.mcpb`-Installationen und lokale MCP-Server für direkte Entwicklung und Tests. Dieses Repository liefert aktuell einen lokalen stdio-MCP-Server; `.mcpb`-Packaging kann später ergänzt werden.

## Ordner Ablage

Lege den entpackten Ordner hier ab:

| Plattform | Ordner |
| --- | --- |
| Windows | `C:\Users\<du>\plugins\icloud-photo-curator` |
| macOS | `~/plugins/icloud-photo-curator` |
| Linux | `~/plugins/icloud-photo-curator` |

## Bootstrap Und Login

Im Plugin-Ordner:

```powershell
python scripts/bootstrap.py
python scripts/try_curator.py login
```

## Claude Desktop Config

Bearbeite die MCP-Konfigurationsdatei von Claude Desktop für deine Plattform.

| Plattform | Häufiger Config-Pfad |
| --- | --- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Nutze absolute Pfade. Windows-Pfade brauchen in JSON doppelte Backslashes.

### Windows Beispiel

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

### macOS Oder Linux Beispiel

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

Für Linux ersetze `/Users/YOUR_NAME` durch `/home/YOUR_NAME`.

## Neustart Und Prüfung

1. Claude Desktop neu starten.
2. Connector- oder Developer-Statusansicht öffnen.
3. Prüfen, ob `icloud-photo-curator` verbunden ist.
4. Claude bitten, `setup_check` auszuführen oder iCloud-Alben zu listen.

## Hinweise

| Thema | Detail |
| --- | --- |
| Passwörter | Werden durch `try_curator.py login` im OS-Keyring gespeichert, nicht in Claude Config |
| 2FA | Wenn die Session abläuft, `try_curator.py login` erneut ausführen oder frischen Code über MCP nutzen |
| Schreibzugriffe | Experimentelle Album-Writes sind standardmäßig Dry-Run und brauchen explizites Env-Flag plus Bestätigungen |
| Packaging | `.mcpb` Desktop-Extension-Packaging ist ein späterer Release-Schritt |

Für Write-Workflows sollte Claude zuerst `write_capabilities` aufrufen, den Dry-Run-Plan zeigen und erst danach genehmigte Vorschläge anwenden, wenn experimentelle Writes bewusst aktiviert wurden. Das Plugin implementiert keine Foto-Löschung.
