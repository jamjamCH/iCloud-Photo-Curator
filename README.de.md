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

**iCloud Photo Curator** ist ein lokales Codex-Plugin und ein MCP-Server für vorsichtige, KI-gestützte iCloud-Fotos-Kuration. Das Plugin liest iCloud-Fotos-Metadaten, scannt Alben, lädt kleine Thumbnails oder Medium-Previews und gibt diese lokalen Bildpfade an Codex oder Claude weiter, damit die KI Vorschläge für die Sortierung machen kann.

Es löscht keine Fotos. Alben erstellen und Fotos zu Alben hinzufügen ist nur über einen **experimentellen, abgesicherten Write-Modus** verfügbar, der standardmäßig als Dry-Run läuft und vor echten iCloud-Änderungen eine explizite Nutzerfreigabe verlangt.

## Überblick

| Bereich | Aktuelles Verhalten |
| --- | --- |
| iCloud-Zugriff | Nutzt `icloudpy` und iCloud-Web/private CloudKit-Endpunkte |
| KI-Bewertung | Der MCP gibt lokale Bildpfade zurück; Codex oder Claude schaut diese im Client an |
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

## Empfohlener Ordner

Wenn du den GitHub-Code als ZIP herunterlädst, entpacke ihn und lege den entpackten Ordner hier ab:

| Plattform | Empfohlener Ordner |
| --- | --- |
| Windows | `C:\Users\<du>\plugins\icloud-photo-curator` |
| macOS | `~/plugins/icloud-photo-curator` |
| Linux | `~/plugins/icloud-photo-curator` |

Wenn GitHub den Ordner als `icloud-photo-curator-main` entpackt, benenne ihn in `icloud-photo-curator` um.

## Schnellstart

Im Plugin-Ordner:

```powershell
python scripts/bootstrap.py
python scripts/try_curator.py login
python scripts/try_curator.py albums
python scripts/try_curator.py prepare --album "All Photos" --limit 10 --version thumb
```

Unter Windows kannst du nach dem Bootstrap auch direkt die virtuelle Umgebung nutzen:

```powershell
.\.venv\Scripts\python.exe .\scripts\try_curator.py setup
```

Unter macOS oder Linux:

```bash
./.venv/bin/python scripts/try_curator.py setup
```

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
| `connect_icloud` | Startet eine iCloud-Session aus Args, Env, `.env` oder Keyring | Nein |
| `validate_2fa_code` | Sendet Apple-2FA-Code und trusted Session, wenn möglich | Nein |
| `list_albums` | Listet iCloud-Fotos-Alben | Nein |
| `scan_album` | Liest Metadaten ohne Originaldownloads | Nein |
| `download_photo_version` | Cached eine kleine Version lokal | Nein |
| `prepare_photo_for_codex` | Bereitet ein Preview für KI-Review vor | Nein |
| `prepare_batch_for_codex` | Bereitet einen kleinen Batch für KI-Review vor | Nein |
| `save_codex_proposal` | Speichert eine lokale Album-Entscheidung | Nein |
| `review_proposals` | Zeigt gespeicherte Vorschläge | Nein |
| `mark_proposals_reviewed` | Markiert Vorschläge lokal als approved/rejected | Nein |
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
