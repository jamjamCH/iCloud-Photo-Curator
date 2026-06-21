# Codex Desktop einrichten (Schritt für Schritt)

Diese Anleitung installiert **iCloud Photo Curator** als lokales Plugin in Codex Desktop. Du brauchst nicht programmieren — kopieren, einfügen, den Schritten folgen.

## Was das für dich macht

Du fragst Codex in normaler Sprache, z. B. *„Sortier meine letzten 10 iCloud-Fotos in Alben."* Codex schaut sich die echten Fotos an und schlägt Alben nach Inhalt vor — Essensfotos kommen in ein **Food**-Album, ein in Paris aufgenommenes Urlaubsfoto wird für ein **Paris**-Album vorgeschlagen, usw.

- Es **löscht nie** Fotos.
- Standardmäßig macht es nur **Vorschläge**; deine Alben ändert es erst nach deiner ausdrücklichen Zustimmung.
- Deine Fotos gehen an keine fremde Firma — das Anschauen übernimmt Codex (das du ohnehin nutzt).

## Was du zuerst brauchst

| Du brauchst | So bekommst du es |
| --- | --- |
| Einen Computer | Windows, macOS oder Linux |
| Python 3.10 oder neuer | Von [python.org](https://www.python.org/downloads/) laden. Unter Windows beim Installieren **„Add Python to PATH"** anhaken. |
| Codex Desktop | Die Codex-App |
| Eine Apple-ID | Die, auf der deine iCloud-Fotos liegen |
| Diesen Projektordner | Auf der GitHub-Seite **Code → Download ZIP** klicken und entpacken |

**Prüfen, ob Python da ist:** Terminal öffnen (macOS/Linux: *Terminal*; Windows: *PowerShell*) und `python --version` eingeben. Erscheint `Python 3.10` oder höher, passt es. Unter macOS evtl. `python3` statt `python`.

## Schritt 1 — Ordner an einen einfachen Ort legen

Verschiebe den entpackten Ordner hierhin:

| Plattform | Ordner |
| --- | --- |
| Windows | `C:\Users\<du>\plugins\icloud-photo-curator` |
| macOS | `~/plugins/icloud-photo-curator` |
| Linux | `~/plugins/icloud-photo-curator` |

Falls der entpackte Ordner `icloud-photo-curator-main` heißt, benenne ihn in `icloud-photo-curator` um.

## Schritt 2 — Installieren und anmelden

Öffne ein Terminal **in diesem Ordner** (Rechtsklick auf den Ordner → *Im Terminal öffnen*, oder mit `cd` dorthin wechseln) und führe aus:

**Windows (PowerShell):**
```powershell
python scripts\bootstrap.py
python scripts\try_curator.py setup
python scripts\try_curator.py login
```

**macOS / Linux:**
```bash
python3 scripts/bootstrap.py
python3 scripts/try_curator.py setup
python3 scripts/try_curator.py login
```

Was passiert:
- `bootstrap.py` legt einen eigenen Arbeitsbereich an (einen Ordner `.venv`) und installiert alles Nötige. **Erwartet:** endet ohne roten Fehler.
- `setup` zeigt einen kurzen Gesundheitscheck (Dependencies, Config, Geocoder).
- `login` fragt nach Apple-ID-E-Mail und Passwort, danach meist nach einem **Apple-2FA-Code** (die 6 Ziffern auf deinem iPhone/Mac). Dein Passwort wird im sicheren Schlüsselbund des Betriebssystems gespeichert — **nie** in einer Textdatei. **Erwartet:** eine Zusammenfassung, die mit `"logged_in": true` endet.

## Schritt 3 — Plugin in die Codex-Marketplace-Datei eintragen

Erstelle oder bearbeite diese Datei (sie ist eine kleine Liste lokaler Plugins, die Codex installieren kann):

| Plattform | Marketplace-Datei |
| --- | --- |
| Windows | `C:\Users\<du>\.agents\plugins\marketplace.json` |
| macOS | `~/.agents/plugins/marketplace.json` |
| Linux | `~/.agents/plugins/marketplace.json` |

Füge das hier ein. Der `path` zeigt auf den Plugin-Ordner aus Schritt 1 (relativ zu deinem Home-Ordner), also entspricht `./plugins/icloud-photo-curator` genau `~/plugins/icloud-photo-curator`:

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

Wenn du schon eine Marketplace-Datei hast, füge nur den einen Eintrag in die bestehende `plugins`-Liste ein (die äußeren Klammern nicht doppeln).

## Schritt 4 — In Codex aktivieren

1. Codex Desktop komplett beenden und neu öffnen.
2. Plugin-Liste öffnen.
3. **iCloud Photo Curator** installieren oder aktivieren.
4. Neue Codex-Session starten und `setup_check` ausführen lassen. **Erwartet:** ein kleiner Bericht mit `"vision_mode": "client_native_mcp_image"`.

## Schritt 5 — Ausprobieren

Tippe Codex z. B. das hier:

> „Scanne meine iCloud-Alben und fasse sie zusammen."

> „Bereite meine nächsten 10 Fotos zur Prüfung vor und schlag Alben vor."

Codex fragt, ob du *nur scannen*, *scannen und vorschlagen* oder *genehmigte Änderungen anwenden* willst. Fang mit Scannen oder Vorschlagen an — in iCloud wird nichts geändert, bis du es sagst.

## Verbindet nicht? Schnelle Lösungen

| Problem | Lösung |
| --- | --- |
| Plugin nicht in der Liste | Prüfe, ob der `path` in `marketplace.json` zum Ordner passt, dann Codex neu starten. |
| `python` nicht gefunden | Nutze `python3` (macOS/Linux) oder installiere Python neu mit „Add to PATH" (Windows). |
| Fragt später erneut nach 2FA | Sessions laufen ab — führe `python scripts/try_curator.py login` erneut aus. |
| Fehler „No iCloud session" | Führe den `login`-Schritt (Schritt 2) aus, bevor du Codex scannen lässt. |

## Was die Tools tun

| Tool | Wofür |
| --- | --- |
| `setup_check` | Gesundheitscheck: Config, Schlüsselbund, Session, Dependencies, Geocoder |
| `connect_icloud` | iCloud-Session öffnen (nutzt deinen gespeicherten Login) |
| `list_albums` | Bestehende Albumnamen lesen |
| `prepare_batch_for_codex` | Einen Batch Fotos als Bilder (+ Metadaten/Ort) schicken, damit Codex sie sieht und sortiert |
| `get_photo_image` | Ein Foto als Bild für einen genauen Blick schicken |
| `save_codex_proposal` | Einen Vorschlag lokal speichern (keine iCloud-Änderung) |
| `review_proposals` | Gespeicherte Vorschläge anzeigen |
| `write_capabilities` / `create_album` / `add_photo_to_album` / `apply_proposals` | Optionale, freiwillige Album-Änderungen (erst Vorschau, dann bestätigen) |

## Gut zu wissen

- **Vision:** `prepare_batch_for_codex` und `get_photo_image` schicken die echten Fotos als Bilder an Codex, sodass es nach dem tatsächlich Sichtbaren sortiert (Essen, Dokumente, Landschaften, …). Kein externer Vision-Dienst.
- **Ortsalben:** GPS wird **offline** in Stadt/Land umgewandelt (über `reverse_geocode`, automatisch installiert), für ortsbasierte Alben.
- **Sicherheit:** Album-Änderungen sind experimentell und freiwillig. Sie brauchen `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true` plus die exakten Bestätigungsphrasen aus `write_capabilities`. Fotos werden nie gelöscht.
