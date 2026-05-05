# Manuelle CLI-Tests

Der CLI-Helfer ist praktisch, bevor der MCP-Server mit Codex oder Claude Desktop verbunden wird.

## Bootstrap

```powershell
python scripts/bootstrap.py
```

## Login

```powershell
python scripts/try_curator.py login
```

Das erstellt oder aktualisiert `~/.icloud-photo-curator/.env`, speichert das iCloud-Passwort im OS-Keyring und validiert 2FA, wenn Apple es verlangt.

## Befehle

| Befehl | Zweck |
| --- | --- |
| `python scripts/try_curator.py setup` | Dependencies, Config, Session-Ordner und Keyring-Status prüfen |
| `python scripts/try_curator.py login` | Apple-ID, Keyring-Passwort und trusted Session einrichten |
| `python scripts/try_curator.py albums` | Alben nach dem Login listen |
| `python scripts/try_curator.py scan --album "All Photos" --limit 5` | Nur Metadaten lesen |
| `python scripts/try_curator.py prepare --album "All Photos" --limit 3 --version thumb` | Kleine Previews für KI-Review cachen |
| `python scripts/try_curator.py review` | Lokal gespeicherte Vorschläge prüfen |
| `python scripts/try_curator.py rules` | Persönliche Sortierregeln anzeigen |
| `python scripts/try_curator.py rules --add "Bevorzuge bestehende Alben."` | Sortierregel ergänzen |
| `python scripts/try_curator.py write-capabilities` | Experimentelle Write-Sicherungen anzeigen |
| `python scripts/try_curator.py create-album --album "Food"` | Album-Erstellung als Dry-Run prüfen |
| `python scripts/try_curator.py add-photo --album "Food" --asset-id <id>` | Ein Foto als Dry-Run hinzufügen |
| `python scripts/try_curator.py apply-proposals <proposal-id>` | Genehmigte Vorschläge als Dry-Run anwenden |

## Experimentelle Writes

Write-Befehle laufen standardmäßig als Dry-Run. Echte Writes brauchen `--execute`, die echte Environment-Variable `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true` außerhalb von `.env` und die exakten `--confirmation`- und `--risk-acknowledgement`-Strings aus:

```powershell
python scripts/try_curator.py write-capabilities
```

Teste echte Writes zuerst nur mit Wegwerf-Alben und winzigen Batches. Die CLI implementiert keine Foto-Löschung.

## 2FA Erneut Versuchen

Wenn Apple außerhalb des Login-Flows nach 2FA fragt:

```powershell
python scripts/try_curator.py albums --two-factor-code 123456
```

## Output-Sicherheit

Die CLI gibt keine Passwörter aus. `setup` zeigt nur, ob wahrscheinlich ein Keyring-Passwort verfügbar ist.
