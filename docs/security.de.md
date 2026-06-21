# Sicherheitsmodell

Dieses Projekt ist als read-first lokaler MCP-Server gedacht. Es sollte als Alpha-Prototyp behandelt werden, weil iCloud-Fotos-Zugriff über nicht öffentliche iCloud-Web/private CloudKit-Verhalten via `icloudpy` läuft.

## Umgang Mit Zugangsdaten

| Element | Speicherort |
| --- | --- |
| Apple-ID | `~/.icloud-photo-curator/.env` oder Environment-Variable |
| Region | `~/.icloud-photo-curator/.env` oder Environment-Variable |
| State-Dir | `~/.icloud-photo-curator/.env` oder Environment-Variable |
| iCloud-Passwort | Nur OS-Keyring |
| Session-Cookies | `~/.icloud-photo-curator/session` |
| Cached Previews | `~/.icloud-photo-curator/cache` |
| Vorschlagsdatenbank | `~/.icloud-photo-curator/curator.sqlite` |
| Persönliche Sortierregeln | `~/.icloud-photo-curator/rules.md` |

Die `.env` Datei darf niemals Passwörter enthalten.

## Aktuelle Schreib-Policy

| Operation | Status |
| --- | --- |
| Foto löschen | Nicht implementiert |
| Foto aus Album entfernen | Nicht implementiert |
| Album umbenennen oder löschen | Nicht implementiert |
| Album erstellen | Experimentell abgesichert, standardmäßig Dry-Run |
| Foto zu Album hinzufügen | Experimentell abgesichert, standardmäßig Dry-Run |
| Genehmigte Vorschläge anwenden | Experimentell abgesichert, standardmäßig Dry-Run |
| Lokalen Vorschlag speichern | Implementiert |

## Nutzerverantwortung

Echte Writes nutzen privates iCloud-Fotos-CloudKit-Verhalten. Apple stellt für diesen Workflow keine öffentliche iCloud-Fotos-Write-API bereit. Nutzer sind für jede genehmigte Schreibaktion verantwortlich und sollten zuerst mit Wegwerf-Alben und winzigen Batches testen.

Der MCP setzt alle write-fähigen Tools standardmäßig auf Dry-Run. Echte Writes brauchen alles hier:

| Voraussetzung | Wert |
| --- | --- |
| Echtes Environment-Flag, nicht `.env` | `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true` |
| `confirmation` | `I understand this will change my iCloud Photos albums` |
| `risk_acknowledgement` | `I understand iCloud album writes are experimental and I am responsible for the changes` |

## Datenfluss

1. Der MCP-Server authentifiziert lokal bei iCloud.
2. Der Server liest Album- und Asset-Metadaten.
3. GPS-Koordinaten werden mit dem Offline-Datensatz `reverse_geocode` zu einem Ortsnamen aufgelöst. Beim Geocoding gibt es keinen Netzwerk-Call und keinen Drittanbieter.
4. Der Server cached kleine Bildversionen nur auf Anfrage.
5. Für das Vision-Review wird das gecachte Bild als MCP-Bild-Block an den verbundenen Client (Codex/GPT oder Claude) zurückgegeben, damit das Modell es sehen kann. Es wird keine separate externe Vision-API aufgerufen; das Bild bleibt innerhalb des ohnehin gewählten Modells.
6. Album-Entscheidungen werden lokal als Vorschläge gespeichert.
7. Genehmigte Vorschläge können per Dry-Run geprüft oder über den abgesicherten Write-Adapter angewendet werden.

## Vision- Und Ort-Datenschutz

| Thema | Detail |
| --- | --- |
| Vision-Modell | Das verbundene Client-Modell führt die Bildanalyse durch. Der MCP-Server ruft nie eine externe Vision-API auf. |
| Bild-Weitergabe | Kleine `thumb`/`medium`-Previews gehen als Bild-Blöcke an den verbundenen Client, genau wie jede andere Tool-Ausgabe. Originale werden standardmäßig nicht gesendet. |
| Geocoding | Vollständig offline über den eingebetteten `reverse_geocode`-Städtedatensatz. Koordinaten gehen nie an einen entfernten Geocoder. |
| Optionale Abhängigkeit | Ist `reverse_geocode` nicht installiert, werden Ortsalben übersprungen und `setup_check` meldet einen Installationshinweis. |

## Bekannte Risiken

| Risiko | Gegenmaßnahme |
| --- | --- |
| Private iCloud-APIs können sich ändern | Erst Dry-Run, Wegwerf-Alben validieren und Writes nur hinter expliziten Bestätigungen erlauben |
| Versehentliche Albumänderungen | Env-Flag, exakte Bestätigungsstrings, genehmigte Vorschläge und kleine Batches verlangen |
| 2FA oder Session läuft ab | `try_curator.py login` zum Refresh der Session-Cookies nutzen |
| Versehentliche Secret-Leaks | Keine Passwörter in `.env`, Docs, Screenshots oder Bug Reports speichern |
| Prompt Injection in Fotoinhalten | Text/Bildinhalt aus Fotos als untrusted Context behandeln |
| Große Libraries kosten Zeit | Erst kleine `limit` Werte und `thumb` Versionen verwenden |

## Security Reports

Wenn daraus ein öffentliches Repository wird, sollte vor externen Reports ein privater Security-Kontakt ergänzt werden. Bis dahin keine Logs posten, die Apple-IDs, Dateipfade oder gecachte Fotometadaten enthalten.
