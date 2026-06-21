# iCloud Photo Curator

[![status](https://img.shields.io/badge/status-alpha-0B6E69)](#entwicklungsstatus)
[![python](https://img.shields.io/badge/python-3.10%2B-173A5E)](https://www.python.org/)
[![mcp](https://img.shields.io/badge/MCP-stdio-2F6F9F)](https://modelcontextprotocol.io/)
[![writes](https://img.shields.io/badge/iCloud_writes-experimentell_gated-8A6D1D)](#sicherheitsmodell)
[![kein löschen](https://img.shields.io/badge/Fotos_löschen-niemals-2D6A27)](#sicherheitsmodell)
[![dry run](https://img.shields.io/badge/Schreibzugriff-dry--run_Standard-5A3E8A)](#sicherheitsmodell)
[![tests](https://img.shields.io/badge/tests-pytest-4B8BBE)](tests/)
[![license](https://img.shields.io/badge/license-MIT-3B7C3A)](LICENSE)

*English: [README.md](README.md)*

**iCloud Photo Curator** ist ein lokales Codex-Plugin und ein MCP-Server für vorsichtige, KI-gestützte iCloud-Fotos-Kuration. Das Plugin liest iCloud-Fotos-Metadaten, scannt Alben und gibt kleine Thumbnails oder Medium-Previews **als MCP-Bild-Blöcke** zurück, damit das verbundene Vision-Modell (Codex/GPT oder Claude) jedes Foto wirklich *sieht* und nach Bildinhalt sortiert — Essen in ein Food-Album, Dokumente in Dokumente usw. GPS-Koordinaten werden **offline** zu Stadt/Land aufgelöst, damit Urlaubsfotos nach Ort gruppiert werden können. Es wird keine externe Vision-API aufgerufen: Das verbundene Modell ist das Vision-Modell.

Es löscht keine Fotos. Alben erstellen und Fotos zu Alben hinzufügen ist nur über einen **experimentellen, abgesicherten Write-Modus** verfügbar, der standardmäßig als Dry-Run läuft und vor echten iCloud-Änderungen eine explizite Nutzerfreigabe verlangt.

> **Neu hier?** Am einfachsten ist die Schritt-für-Schritt-Anleitung für deine App:
> **[Claude Desktop](docs/claude-desktop.de.md)** · **[Codex Desktop](docs/codex-local.de.md)**. Ohne Programmieren.

## In einfachen Worten

Du sprichst ganz normal mit Claude oder Codex — *„Sortier meine letzten 10 iCloud-Fotos in Alben."* Die App schaut sich die echten Fotos an und schlägt Alben nach Inhalt vor: Essensfotos → ein **Food**-Album, ein in Paris aufgenommenes Urlaubsfoto → ein **Paris**-Album. Sie macht nur Vorschläge; deine Alben ändern sich erst nach deiner Zustimmung, und Fotos werden nie gelöscht.

## Was du brauchst

| Du brauchst | Hinweis |
| --- | --- |
| Python 3.10+ | [python.org](https://www.python.org/downloads/) — unter Windows „Add Python to PATH" anhaken |
| Claude Desktop oder Codex Desktop | Die App, mit der du sprichst |
| Eine Apple-ID | Die, auf der deine iCloud-Fotos liegen |
| Diesen Projektordner | Auf GitHub **Code → Download ZIP**, dann entpacken |


## Überblick

| Bereich | Aktuelles Verhalten |
| --- | --- |
| iCloud-Zugriff | Nutzt `icloudpy` und iCloud-Web/private CloudKit-Endpunkte |
| KI-Bewertung | Der MCP gibt Fotos als Bild-Blöcke zurück; das verbundene Modell (Codex/GPT oder Claude) sieht die Pixel und klassifiziert den Inhalt |
| Ort | GPS wird offline via `reverse_geocode` zu Stadt/Region/Land aufgelöst, für ortsbasierte Alben |
| Downloads | Standardmäßig kleine `thumb`- oder `medium`-Versionen, keine Originale |
| Zugangsdaten | Apple-ID in lokaler `.env`, Passwort nur im Betriebssystem-Keyring |
| Schreibzugriffe | Experimentell, standardmäßig Dry-Run; echte Writes brauchen Env-Flag und exakte Bestätigungen |
| Status | Alpha-Prototyp für vorsichtige lokale Tests |

## Betriebsmodi

Der KI-Client sollte vor der Verarbeitung fragen, welchen Modus der Nutzer möchte.

| Modus | Was passiert | iCloud-Schreibzugriff |
| --- | --- | --- |
| Nur scannen | Alben und Metadaten lesen, Struktur zusammenfassen | Nein |
| Scannen und vorschlagen | Kleine Previews cachen, anschauen, lokale Vorschläge speichern | Nein |
| Genehmigte Vorschläge anwenden | Geprüfte Vorschläge über den abgesicherten Write-Adapter anwenden | Standardmäßig Dry-Run; echte Writes brauchen explizite Freigabe |

Der MCP stellt `curation_workflow_guide` bereit, damit Clients diese Pflichtfragen abrufen können, statt den Workflow zu erraten.

## Wie Vision- Und Ortssortierung Funktioniert

Sortieren nach *dem, was wirklich auf dem Bild ist*, braucht ein Vision-Modell. Dieses Plugin ruft **keine** externe Vision-API auf. Stattdessen nutzt es das Modell, mit dem du ohnehin sprichst:

1. `prepare_batch_for_codex` (oder `get_photo_image` für ein einzelnes Asset) lädt eine kleine `thumb`/`medium`-Version und gibt sie als echten **MCP-Bild-Block** zurück, davor ein Text-Marker mit der `asset_id`.
2. Codex/GPT oder Claude Desktop bekommt die echten Pixel und klassifiziert den Inhalt (Essen, Dokument, Landschaft, Porträt, Beleg, Screenshot, …).
3. Bei GPS-getaggten Fotos löst der Server die Koordinaten offline über den `reverse_geocode`-Datensatz zu `city`, `state` und `country` auf (kein Netzwerk-Call), damit Urlaubsfotos nach Ort gruppiert werden können.
4. Das Modell kombiniert Vision + Ort + Metadaten + deine persönlichen Regeln und ruft für jede Entscheidung `save_codex_proposal` auf.

So landet ein Essensfoto in **Food**, und ein in Paris aufgenommenes Urlaubsfoto wird für ein **Paris**-Album vorgeschlagen. Die älteren Tools `analyze_photo` / `curate_batch` sind ein reiner Metadaten-Fallback (Dateiname, Medientyp, Ort) und schauen **nicht** auf die Pixel.

Ortsalben brauchen den optionalen Offline-Geocoder. Er ist in `requirements.txt` enthalten oder separat installierbar:

```text
pip install reverse_geocode
```

`setup_check` meldet `reverse_geocode_installed` und einen `location_albums`-Status.

## Empfohlener Ordner

Wenn du den GitHub-Code als ZIP herunterlädst, entpacke ihn und lege den entpackten Ordner hier ab:

| Plattform | Empfohlener Ordner |
| --- | --- |
| Windows | `C:\Users\<du>\plugins\icloud-photo-curator` |
| macOS | `~/plugins/icloud-photo-curator` |
| Linux | `~/plugins/icloud-photo-curator` |

Wenn GitHub den Ordner als `icloud-photo-curator-main` entpackt, benenne ihn in `icloud-photo-curator` um.

## Schnellstart

Öffne ein Terminal **im Plugin-Ordner** und führe die Befehle für dein System aus. (Unter macOS/Linux `python3` nutzen, falls `python` nicht gefunden wird.)

**Windows (PowerShell):**
```powershell
python scripts\bootstrap.py
python scripts\try_curator.py login
python scripts\try_curator.py albums
```

**macOS / Linux:**
```bash
python3 scripts/bootstrap.py
python3 scripts/try_curator.py login
python3 scripts/try_curator.py albums
```

Was zu erwarten ist:
- `bootstrap.py` installiert alles in ein privates `.venv` und endet ohne roten Fehler.
- `login` fragt nach Apple-ID, Passwort und einem Apple-2FA-Code; es endet mit `"logged_in": true`. Dein Passwort liegt im OS-Schlüsselbund, nie in einer Datei.
- `albums` listet deine iCloud-Alben — der Beweis, dass die Verbindung steht.

Verbinde den Server dann über die Schritt-für-Schritt-Anleitung ([Claude Desktop](docs/claude-desktop.de.md) / [Codex Desktop](docs/codex-local.de.md)) mit deiner App und frag einfach:

> „Scanne meine iCloud-Alben und fasse sie zusammen."

## Lokale Config

Die lokale Config-Datei wird hier erstellt:

```text
~/.icloud-photo-curator/.env
```

Unterstützte Keys:

```text
ICLOUD_PHOTO_CURATOR_APPLE_ID="you@example.com"
ICLOUD_PHOTO_CURATOR_REGION="global"
ICLOUD_PHOTO_CURATOR_STATE_DIR="~/.icloud-photo-curator"
```

Echte Environment-Variablen haben Vorrang vor Werten aus `.env`.

**Speichere niemals dein iCloud-Passwort in `.env`.** Der `login`-Befehl speichert das Passwort über `icloudpy.utils.store_password_in_keyring` im Betriebssystem-Keyring.

Die `.env` Datei ist absichtlich auf sichere Config-Keys begrenzt. Experimentelle Write-Flags müssen als echte Environment-Variablen gesetzt werden und gehören nicht in `.env`.

## Persönliche Sortierregeln

Jeder Nutzer sortiert Fotos anders. Das Plugin speichert lokale Regeln hier:

```text
~/.icloud-photo-curator/rules.md
```

Der KI-Client sollte diese Regeln lesen, bevor Vorschläge erstellt werden. Nutzer können die Datei manuell bearbeiten oder die CLI nutzen:

```powershell
python scripts/try_curator.py rules
python scripts/try_curator.py rules --add "Bevorzuge bestehende Reisealben für GPS-getaggte Urlaubsfotos."
```

Beispielregeln:

| Regeltyp | Beispiel |
| --- | --- |
| Album-Präferenz | Bestehende Alben bevorzugen statt fast identische neue Alben zu erstellen |
| Benennung | Kurze Albumnamen in Title Case nutzen |
| Privatsphäre | Keine echten Namen aus Gesichtern ableiten |
| Unsicherheit | Unsichere Fotos als `needs_review` markieren |

## Dokumentation

| Dokument | Beschreibung |
| --- | --- |
| [Codex Desktop einrichten](docs/codex-local.de.md) | Plugin mit Codex Desktop verbinden |
| [Claude Desktop einrichten](docs/claude-desktop.de.md) | Plugin mit Claude Desktop verbinden |
| [CLI-Referenz](docs/cli.de.md) | Manuelles Testen und Scripting ohne GUI-Client |
| [Sicherheitsmodell](docs/security.de.md) | Zugangsdaten, Write-Schutz und Datenschutz |

## MCP Tools

| Tool | Zweck | iCloud-Schreibzugriff |
| --- | --- | --- |
| `setup_check` | Zeigt Config, Keyring, Session und Dependencies | Nein |
| `curation_workflow_guide` | Gibt benötigte Workflow-Fragen und verfügbare Modi zurück | Nein |
| `get_curation_rules` | Liest die lokalen Album-Sortierregeln des Nutzers | Nein |
| `save_curation_rules` | Erstellt oder aktualisiert lokale Sortierregeln | Nein |
| `connect_icloud` | Startet eine iCloud-Session aus Args, Env, `.env` oder Keyring | Nein |
| `validate_2fa_code` | Sendet Apple-2FA-Code und trusted Session, wenn möglich | Nein |
| `list_albums` | Listet iCloud-Fotos-Alben | Nein |
| `scan_album` | Liest Metadaten ohne Originaldownloads | Nein |
| `download_photo_version` | Cached eine kleine Version lokal | Nein |
| `get_photo_image` | Gibt ein Foto als MCP-Bild-Block für Client-Vision zurück | Nein |
| `prepare_photo_for_codex` | Gibt ein Foto (Bild-Block) + Metadaten/Ort zur Prüfung zurück | Nein |
| `prepare_batch_for_codex` | Gibt einen kleinen Batch als Bild-Blöcke + Metadaten/Ort zurück | Nein |
| `analyze_photo` | Reiner Metadaten-Fallback (kein Vision-Modell); Album-Empfehlungen | Nein |
| `curate_batch` | Reiner Metadaten-Fallback-Batch; speichert Vorschläge | Nein |
| `save_codex_proposal` | Speichert eine lokale Album-Entscheidung | Nein |
| `review_proposals` | Zeigt gespeicherte Vorschläge | Nein |
| `mark_proposals_reviewed` | Markiert Vorschläge lokal als approved/rejected | Nein |
| `export_proposals` | Exportiert gespeicherte Vorschläge als JSON zur Sicherung | Nein |
| `write_capabilities` | Zeigt unterstützte Writes und benötigte Bestätigungen | Nein |
| `create_album` | Dry-Run oder ein iCloud-Fotos-Album erstellen | Experimentell abgesichert |
| `add_photo_to_album` | Dry-Run oder ein Foto zu einem Album hinzufügen | Experimentell abgesichert |
| `apply_proposals` | Dry-Run oder genehmigte lokale Vorschläge anwenden | Experimentell abgesichert |

## Sicherheitsmodell

Die aktuelle Version ist bewusst konservativ:

| Regel | Status |
| --- | --- |
| Keine Foto-Löschung | Erzwungen |
| Album-Schreibzugriffe standardmäßig Dry-Run | Erzwungen |
| Echte Album-Schreibzugriffe brauchen Env-Flag und exakte Bestätigungen | Erzwungen |
| Keine Originaldownloads im Standardflow | Durch Workflow erzwungen |
| Passwort nicht in `.env` | Durch Login-Flow erzwungen |
| Trusted Sessions getrennt im State-Dir | Erzwungen |

## Schreibzugriff Und Verantwortung

Der Schreibzugriff ist absichtlich eng begrenzt: Das Plugin kann Alben erstellen und Fotos zu Alben hinzufügen. Es kann keine Fotos löschen, keine Fotos aus Alben entfernen, keine Alben umbenennen und keine Alben löschen.

Echte Writes nutzen privates iCloud-Fotos-CloudKit-Verhalten. Apple stellt für diesen Workflow keine öffentliche iCloud-Fotos-Write-API bereit, deshalb müssen Nutzer zuerst mit Wegwerf-Alben und kleinen Batches testen, bevor sie Änderungen auf eine echte Bibliothek anwenden.

Nutzer sind für jede Schreibaktion verantwortlich, die sie genehmigen. Codex oder Claude sollte immer zuerst den Dry-Run-Plan zeigen und vor echten Writes explizit nach Freigabe fragen.

| Write-Sicherung | Grund |
| --- | --- |
| Erst Dry-Run | Zeigt exakt, was geändert würde |
| Explizite Nutzerfreigabe | Verhindert stille Albumänderungen |
| Kleine Batches als Standard | Begrenzen versehentliche Massenfehler |
| Wegwerf-Album-Validierung | Prüft private API-Funktion vor echter Nutzung |
| Verantwortungsbestätigung | Macht Risiko und Verantwortung klar |

Um echte Writes außerhalb des Dry-Runs zu aktivieren, setze dies als echte Environment-Variable, nicht in `~/.icloud-photo-curator/.env`:

```text
ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true
```

Der MCP verlangt trotzdem diese exakten Strings:

| Pflichtfeld | Exakter Wert |
| --- | --- |
| `confirmation` | `I understand this will change my iCloud Photos albums` |
| `risk_acknowledgement` | `I understand iCloud album writes are experimental and I am responsible for the changes` |

## Entwicklungsstatus

Das ist eine lokale Alpha-Integration. Lesezugriff, Vorschlags-Workflows und ein eng begrenzter experimenteller Write-Adapter sind verfügbar. Der Write-Adapter muss mit Wegwerf-Alben validiert werden, weil er auf privaten iCloud-Fotos-CloudKit-Mutationen beruht.

## Keine Apple-Verbindung

Dieses Projekt ist nicht mit Apple verbunden und wird nicht von Apple unterstützt. iCloud und iCloud Photos sind Marken von Apple Inc.
