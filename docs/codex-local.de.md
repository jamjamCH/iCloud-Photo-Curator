# Codex Desktop Lokale Installation

Diese Anleitung installiert **iCloud Photo Curator** als lokales Codex-Plugin.

## Ordner Ablage

Lege den entpackten Ordner hier ab:

| Plattform | Ordner |
| --- | --- |
| Windows | `C:\Users\<du>\plugins\icloud-photo-curator` |
| macOS | `~/plugins/icloud-photo-curator` |
| Linux | `~/plugins/icloud-photo-curator` |

Falls der entpackte Ordner `icloud-photo-curator-main` heißt, benenne ihn in `icloud-photo-curator` um.

## Bootstrap

Im Plugin-Ordner:

```powershell
python scripts/bootstrap.py
python scripts/try_curator.py setup
python scripts/try_curator.py login
```

## Codex Marketplace Eintrag

Erstelle oder aktualisiere:

| Plattform | Marketplace-Datei |
| --- | --- |
| Windows | `C:\Users\<du>\.agents\plugins\marketplace.json` |
| macOS | `~/.agents/plugins/marketplace.json` |
| Linux | `~/.agents/plugins/marketplace.json` |

Minimale Marketplace-Datei:

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

Wenn du bereits eine Marketplace-Datei hast, füge nur den Plugin-Eintrag in das bestehende `plugins` Array ein.

## In Codex Aktivieren

1. Codex Desktop neu starten.
2. Plugin-Liste öffnen.
3. **iCloud Photo Curator** installieren oder aktivieren.
4. Neue Codex-Session starten und iCloud verbinden lassen.

## Erwartete Befehle

Nach dem Setup sollte Codex MCP-Tools aufrufen können:

| Tool | Erwarteter Nutzen |
| --- | --- |
| `setup_check` | `.env`, Keyring, Session, Dependencies und Geocoder prüfen |
| `connect_icloud` | Session ohne Username/Passwort-Argumente öffnen |
| `list_albums` | Bestehende Alben lesen |
| `prepare_batch_for_codex` | Batch als Bild-Blöcke + Metadaten/Ort zurückgeben, damit Codex sie sieht |
| `get_photo_image` | Ein Foto als Bild-Block für präzises Inhalts-Review zurückgeben |
| `save_codex_proposal` | Lokale Vorschläge speichern |
| `write_capabilities` | Prüfen, ob experimentelle Writes aktiviert sind |
| `create_album` | Dry-Run oder nach expliziter Freigabe ein Album erstellen |
| `add_photo_to_album` | Dry-Run oder nach expliziter Freigabe ein Foto hinzufügen |
| `apply_proposals` | Dry-Run oder genehmigte lokale Vorschläge anwenden |

## Vision Und Ort

`prepare_batch_for_codex` und `get_photo_image` geben die echten Fotos als MCP-Bild-Blöcke zurück, sodass Codex die Pixel sieht und nach sichtbarem Inhalt sortiert (Essen, Dokumente, Landschaften, …). GPS wird offline zu Stadt/Land aufgelöst, für ortsbasierte Alben. Optionalen Geocoder installieren: `pip install reverse_geocode` (bereits in `requirements.txt`).

## Sicherheit

Codex sollte mit `curation_workflow_guide` starten, fragen ob der Nutzer nur scannen, Vorschläge erstellen oder genehmigte Writes anwenden möchte, und Write-Tools zuerst als Dry-Run ausführen.

Echte iCloud-Album-Writes sind experimentell. Sie brauchen `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true` plus die exakte Bestätigung und Risiko-Anerkennung aus `write_capabilities`. Das Plugin implementiert keine Foto-Löschung.
