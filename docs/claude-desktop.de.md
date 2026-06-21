# Claude Desktop einrichten (Schritt für Schritt)

Diese Anleitung verbindet **iCloud Photo Curator** mit Claude Desktop. Du brauchst nicht programmieren — nur kopieren, einfügen und den Schritten folgen.

## Was das für dich macht

Du sprichst mit Claude in normaler Sprache, z. B. *„Sortier meine letzten 10 iCloud-Fotos in Alben."* Claude schaut sich die echten Fotos an und schlägt dann Alben vor, je nach Inhalt — Essensfotos kommen in ein **Food**-Album, ein in Paris aufgenommenes Urlaubsfoto wird für ein **Paris**-Album vorgeschlagen, usw.

- Es **löscht nie** Fotos.
- Standardmäßig macht es nur **Vorschläge**; deine Alben ändert es erst, wenn du ausdrücklich zustimmst.
- Deine Fotos gehen an keine fremde Firma — das Anschauen übernimmt Claude (das du ohnehin nutzt).

## Was du zuerst brauchst

| Du brauchst | So bekommst du es |
| --- | --- |
| Einen Computer | Windows, macOS oder Linux |
| Python 3.10 oder neuer | Von [python.org](https://www.python.org/downloads/) laden. Unter Windows beim Installieren **„Add Python to PATH"** anhaken. |
| Claude Desktop | Die Desktop-App von Anthropic |
| Eine Apple-ID | Die, auf der deine iCloud-Fotos liegen |
| Diesen Projektordner | Auf der GitHub-Seite **Code → Download ZIP** klicken und entpacken |

**Prüfen, ob Python da ist:** Terminal öffnen (macOS/Linux: *Terminal*; Windows: *PowerShell*) und `python --version` eingeben. Erscheint `Python 3.10` oder höher, passt es. Unter macOS musst du evtl. `python3` statt `python` schreiben.

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
python scripts\try_curator.py login
```

**macOS / Linux:**
```bash
python3 scripts/bootstrap.py
python3 scripts/try_curator.py login
```

Was passiert:
- `bootstrap.py` legt einen eigenen Arbeitsbereich an (einen Ordner `.venv`) und installiert alles Nötige. **Erwartet:** es endet ohne roten Fehler.
- `login` fragt nach deiner Apple-ID-E-Mail und deinem Passwort, danach meist nach einem **Apple-2FA-Code** (die 6 Ziffern, die auf deinem iPhone/Mac erscheinen). Tippe ihn ein. Dein Passwort wird im sicheren Schlüsselbund deines Betriebssystems gespeichert — **nie** in einer Textdatei.
- **Erwartetes Ergebnis:** eine kurze Zusammenfassung, die mit `"logged_in": true` endet.

## Schritt 3 — Claude Desktop den Server bekannt machen

Öffne die Konfigurationsdatei von Claude Desktop (lege sie an, falls sie fehlt):

| Plattform | Konfigurationsdatei |
| --- | --- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Füge den Block für dein System ein und **ersetze `YOUR_NAME`** durch deinen echten Benutzernamen. Nutze vollständige Pfade (Windows braucht doppelte Backslashes).

**Windows:**
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

**macOS / Linux** (unter Linux `/Users/YOUR_NAME` durch `/home/YOUR_NAME` ersetzen):
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

## Schritt 4 — Neu starten und prüfen

1. Claude Desktop komplett beenden und neu öffnen.
2. Connector-/Developer-Ansicht öffnen und prüfen, dass **icloud-photo-curator** als verbunden angezeigt wird.
3. Bitte Claude im Chat, `setup_check` auszuführen. **Erwartet:** ein kleiner Bericht mit `"vision_mode": "client_native_mcp_image"`.

## Schritt 5 — Ausprobieren

Tippe Claude z. B. das hier:

> „Scanne meine iCloud-Alben und fasse sie zusammen."

> „Bereite meine nächsten 10 Fotos zur Prüfung vor und schlag Alben vor."

Claude fragt, ob du *nur scannen*, *scannen und vorschlagen* oder *genehmigte Änderungen anwenden* willst. Fang mit Scannen oder Vorschlagen an — in iCloud wird nichts geändert, bis du es sagst.

## Einfacher: Ein-Klick-Installation (.mcpb, experimentell)

Statt die Config in Schritt 3 von Hand zu bearbeiten, kannst du eine fertige Extension installieren. Das ist **experimentell**: Python muss trotzdem installiert sein, und beim ersten Start werden die Abhängigkeiten in einen privaten Arbeitsbereich geladen (der erste Start dauert daher kurz und braucht Internet).

1. Hol dir die `.mcpb`-Datei — von der **Releases**-Seite des Projekts laden, oder selbst im Projektordner bauen:
   - Windows: `python scripts\build_mcpb.py`
   - macOS / Linux: `python3 scripts/build_mcpb.py`

   Sie landet unter `dist/icloud-photo-curator-<version>.mcpb`.
2. In Claude Desktop **Einstellungen → Erweiterungen** öffnen und die `.mcpb`-Datei hineinziehen (oder doppelklicken). Apple-ID eingeben, falls gefragt.
3. Führe den einmaligen `login` (Schritt 2) trotzdem einmal aus, damit dein Passwort im OS-Schlüsselbund liegt.

Wenn etwas hakt, nutze die manuelle Config aus Schritt 3 — das ist der zuverlässige Weg.

## Verbindet nicht? Schnelle Lösungen

| Problem | Lösung |
| --- | --- |
| Server nicht in Claude sichtbar | Prüfe die JSON-Pfade und ob du Claude wirklich komplett neu gestartet hast. |
| `python` nicht gefunden | Nutze `python3` (macOS/Linux) oder installiere Python neu mit „Add to PATH" (Windows). |
| Fragt später erneut nach 2FA | Sessions laufen ab — führe einfach `python scripts/try_curator.py login` erneut aus. |
| Fehler „No iCloud session" | Führe den `login`-Schritt (Schritt 2) aus, bevor du Claude scannen lässt. |

## Gut zu wissen

- **Vision:** Die Tools `prepare_batch_for_codex` und `get_photo_image` schicken das Foto als Bild an Claude, sodass Claude nach dem tatsächlichen Bildinhalt sortiert. Es wird kein externer Vision-Dienst genutzt.
- **Ortsalben:** GPS wird **offline** in Stadt/Land umgewandelt (über `reverse_geocode`, automatisch installiert), damit Reisen nach Ort gruppiert werden.
- **Sicherheit:** Album-Änderungen sind eine experimentelle, freiwillige Funktion. Sie bleibt in der Vorschau („Dry-Run"), bis du sie aktivierst und bestätigst. Fotos werden nie gelöscht.
