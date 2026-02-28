# Mite to Alphaflow Invoice CLI

CLI-Programm zum Erstellen von Alphaflow-Rechnungen aus mite Zeiteinträgen.

## Features

- Holt Zeiteinträge aus mite für ein bestimmtes Projekt und einen Datumsbereich
- Filtert nach billable/non-billable Einträgen
- Erstellt automatisch eine Rechnung im Alphaflow Rechnungsprogramm
- Trading Partner Auswahl: Per ID oder Number direkt übergeben, oder Default aus Config
- **Automatisches Sperren der abgerechneten Zeiteinträge in mite**
- Dry-Run Modus zum Testen ohne Rechnungserstellung
- Benutzerfreundliche CLI mit Rich-Formatierung
- Umfassende Validierung und Fehlerbehandlung

## Installation

1. Python 3.8+ erforderlich

2. Dependencies installieren:
```bash
pip install -r requirements.txt
```

## Konfiguration

### 1. Umgebungsvariablen (.env)

Erstelle eine `.env` Datei im Projekt-Verzeichnis:

```bash
cp .env.example .env
```

Bearbeite die `.env` Datei und füge deine API-Keys ein:

```bash
MITE_API_KEY=your_mite_api_key_here
DVELOP_API_KEY=your_dvelop_api_key_here
```

**Wo finde ich die API-Keys?**
- **Mite API Key**: https://YOUR_ACCOUNT.mite.de/myself (z.B. https://alphaflow.mite.de/myself)
- **d.velop/Alphaflow API Key**: Kontaktiere deinen Alphaflow Administrator

### 2. Konfigurationsdatei (config.yaml)

Erstelle eine `config.yaml` aus der Beispiel-Konfiguration:

```bash
cp config_example.yaml config.yaml
```

Passe die Werte in `config.yaml` an:

```yaml
mite:
  account: "alphaflow"  # Dein mite Account-Name
  api_key: "${MITE_API_KEY}"

alphaflow:
  dvelop_base_url: "https://alphaflow-test.d-velop.cloud"
  dvelop_api_key: "${DVELOP_API_KEY}"
  organization_id: "5f3a530a83809e7e377788a5"
  responsible_administrator_id: "78728E3E-4025-4B19-B969-74C64E459A40"

  default_hourly_rate: 190.0
  default_vat_rate: 19.0
  default_due_days: 30
  default_currency: "EUR"

  default_trading_partner_id: "5f438d2fc40da20fc4efc338"

logging:
  level: "INFO"
```

**Wichtige Felder:**
- `default_trading_partner_id`: Standard Trading Partner, wenn kein `--trading-partner-id` oder `--trading-partner-number` übergeben wird

## Verwendung

### Basis-Aufruf

```bash
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31
```

### Alle Optionen

```bash
# Nur billable Einträge (Standard)
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31

# Alle Einträge (auch nicht-billable)
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 --no-billable-only

# Dry-Run (nur Vorschau, keine Rechnung erstellen)
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 --dry-run

# Verbose Ausgabe
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 --verbose

# Trading Partner Override mit ID (überschreibt Mapping)
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 \
  --trading-partner-id "5f438d2fc40da20fc4efc338"

# Trading Partner Override mit Number (wird zu ID aufgelöst)
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 \
  --trading-partner-number "000001"

# Eigene Config-Datei
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 \
  --config ./my-config.yaml
```

### Parameter

| Parameter | Kurz | Beschreibung | Pflicht | Default |
|-----------|------|--------------|---------|---------|
| `--project-id` | `-p` | mite Projekt-ID | Ja | - |
| `--from` | `-f` | Start-Datum (YYYY-MM-DD) | Ja | - |
| `--to` | `-t` | End-Datum (YYYY-MM-DD) | Ja | - |
| `--config` | `-c` | Pfad zur config.yaml | Nein | `./config.yaml` |
| `--billable-only` | - | Nur billable Einträge | Nein | `True` |
| `--no-billable-only` | - | Alle Einträge inkl. non-billable | Nein | - |
| `--dry-run` | - | Nur Vorschau, keine Erstellung | Nein | `False` |
| `--verbose` | `-v` | Detaillierte Ausgabe | Nein | `False` |
| `--trading-partner-id` | - | Trading Partner ID Override | Nein | - |
| `--trading-partner-number` | - | Trading Partner Number (wird zu ID aufgelöst) | Nein | - |

### Version anzeigen

```bash
python create_invoice.py version
```

## Workflow

Das Programm führt folgende Schritte aus:

1. **Konfiguration laden**: Lädt `config.yaml` und `.env`
2. **Datums-Validierung**: Prüft, ob Datumsbereich gültig ist
3. **Zeiteinträge holen**: Holt **nur nicht-gesperrte** Zeiteinträge aus mite API
4. **Daten aggregieren**: Fasst Zeiteinträge pro Projekt zusammen
5. **Trading Partner bestimmen**: Über Mapping oder Default
6. **Alphaflow authentifizieren**: Authentifizierung mit d.velop Cloud
7. **Rechnung erstellen**: Erstellt Rechnung im Alphaflow System
8. **Zeiteinträge sperren**: Sperrt automatisch alle abgerechneten Zeiteinträge in mite

### Schutz vor Doppel-Abrechnung

**Wichtig:** Das Tool berücksichtigt automatisch nur **nicht-gesperrte** Zeiteinträge bei der Rechnungserstellung. Dies verhindert, dass bereits abgerechnete Zeiten versehentlich doppelt abgerechnet werden.

**Wie funktioniert der Schutz:**
1. Beim Abrufen der Zeiteinträge werden nur Einträge mit `locked=false` berücksichtigt
2. Bereits gesperrte Einträge (z.B. aus früheren Rechnungen) werden automatisch ignoriert
3. Nach erfolgreicher Rechnungserstellung werden die verwendeten Einträge gesperrt
4. Bei einem erneuten Abruf für denselben Zeitraum werden diese Einträge nicht mehr gefunden

**Beispiel:**
```bash
# Erste Rechnung für Januar - findet 42 Einträge
python create_invoice.py --project-id 12345 --from 2024-01-01 --to 2024-01-31
✓ Found 42 time entries (unlocked only)
✓ All time entries locked successfully

# Zweite Rechnung für Januar - findet 0 Einträge
python create_invoice.py --project-id 12345 --from 2024-01-01 --to 2024-01-31
⚠ No unlocked time entries found for project 12345
Note: Locked entries are excluded. They may have been invoiced already.
```

### Automatisches Sperren von Zeiteinträgen

Nach der erfolgreichen Erstellung einer Rechnung werden automatisch alle Zeiteinträge, die in die Rechnung eingeflossen sind, in mite gesperrt (locked).

**Was passiert beim Sperren:**
- Alle Zeiteinträge, die in die Rechnung geflossen sind, werden mit `locked=True` markiert
- Bereits gesperrte Einträge werden übersprungen
- Falls einzelne Einträge nicht gesperrt werden können, wird eine Warnung ausgegeben
- Die Rechnung wird trotzdem erfolgreich erstellt, auch wenn Einträge nicht gesperrt werden konnten

**Beispiel-Output:**
```
Locking time entries in mite...

┌────────────────────────────────────────┐
│       Time Entries Locked              │
├──────────────────┬─────────────────────┤
│ Status           │ Count               │
├──────────────────┼─────────────────────┤
│ Total entries    │ 42                  │
│ Newly locked     │ 40                  │
│ Already locked   │ 2                   │
└──────────────────┴─────────────────────┘

✓ All time entries locked successfully
```

## Beispiel-Output

```
Loading configuration...
✓ Configuration loaded successfully

Fetching time entries from mite...
  Project ID: 12345
  Date range: 2024-12-01 to 2024-12-31
  Billable only: True
✓ Found 42 time entries

Aggregating project data...
✓ Trading partner mapped: 5f438d2fc40da20fc4efc338

┌────────────────────────────────────────┐
│          Project Summary               │
├──────────────────┬─────────────────────┤
│ Field            │ Value               │
├──────────────────┼─────────────────────┤
│ Project Name     │ Client Project XYZ  │
│ Project ID       │ 12345               │
│ Customer         │ Client ABC          │
│ Total Hours      │ 123.45h             │
│ Total Revenue    │ 23455.50 EUR        │
│ Trading Partner  │ 5f438d2fc40da20fc4… │
└──────────────────┴─────────────────────┘

Authenticating with Alphaflow...
✓ Authentication successful

Creating invoice in Alphaflow...

✓ Invoice created successfully!

┌────────────────────────────────────────┐
│          Invoice Details               │
├──────────────────┬─────────────────────┤
│ Invoice ID       │ 65f3a...            │
│ Project          │ Client Project XYZ  │
│ Hours            │ 123.45h             │
│ Amount           │ 23455.50 EUR        │
│ Trading Partner  │ 5f438d2fc40da20fc4… │
└──────────────────┴─────────────────────┘

Locking time entries in mite...

┌────────────────────────────────────────┐
│       Time Entries Locked              │
├──────────────────┬─────────────────────┤
│ Status           │ Count               │
├──────────────────┼─────────────────────┤
│ Total entries    │ 42                  │
│ Newly locked     │ 42                  │
│ Already locked   │ 0                   │
└──────────────────┴─────────────────────┘

✓ All time entries locked successfully
```

## Dry-Run Modus

Mit `--dry-run` kannst du testen, welche Rechnung erstellt werden würde, ohne sie tatsächlich zu erstellen:

```bash
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 --dry-run
```

Output:

```
DRY-RUN MODE - No invoice will be created

┌──────────────────────────────────────┐
│        Invoice Preview               │
├──────────────────────────────────────┤
│ Project: Client Project XYZ          │
│ Hours: 123.45h                       │
│ Amount: 23455.50 EUR                 │
│ Trading Partner: 5f438d2fc40da20fc4… │
│ Service Period: 2024-12-01 to …     │
│ Invoice Date: 2025-01-22             │
└──────────────────────────────────────┘

✓ Dry-run completed successfully
```

## Troubleshooting

### Fehler: "Config file not found"

**Problem**: `config.yaml` wurde nicht gefunden

**Lösung**:
```bash
cp config_example.yaml config.yaml
# Dann config.yaml anpassen
```

### Fehler: "Environment variable 'MITE_API_KEY' not found"

**Problem**: API-Key nicht in `.env` gesetzt

**Lösung**:
```bash
cp .env.example .env
# Dann .env mit echten API-Keys füllen
```

### Fehler: "No time entries found"

**Problem**: Keine Zeiteinträge für das Projekt im angegebenen Zeitraum

**Mögliche Ursachen**:
- Falsches Datum
- Falsche Projekt-ID
- Keine billable Einträge (versuche `--no-billable-only`)

**Lösung**: Überprüfe Projekt-ID und Datumsbereich in mite

### Fehler: "Authentication failed"

**Problem**: d.velop/Alphaflow Authentifizierung fehlgeschlagen

**Mögliche Ursachen**:
- Falscher API-Key
- Falsche Base-URL
- Netzwerkprobleme

**Lösung**: Überprüfe `dvelop_api_key` und `dvelop_base_url` in `config.yaml`

### Fehler: "Configuration validation failed"

**Problem**: Config-Datei enthält ungültige Werte

**Lösung**: Überprüfe die Fehlermeldung und korrigiere die entsprechenden Felder in `config.yaml`

### Info: "Using default trading partner"

**Info**: Es wurde kein `--trading-partner-id` oder `--trading-partner-number` angegeben, daher wird der Default Trading Partner aus der Config verwendet

**Lösung (optional)**: Gib den Trading Partner explizit an:
```bash
# Mit Trading Partner ID
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 \
  --trading-partner-id "5f438d2fc40da20fc4efc338"

# Oder mit Trading Partner Number
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 \
  --trading-partner-number "30001"
```

## Entwicklung

### Struktur

```
alphaflow_create_mite_invoice/
├── create_invoice.py               # Haupt-CLI-Programm
├── config.yaml                     # Deine Konfiguration (gitignored)
├── config_example.yaml             # Beispiel-Konfiguration
├── requirements.txt                # Python-Dependencies
├── .env                            # Umgebungsvariablen (gitignored)
├── .env.example                    # Beispiel .env
├── .gitignore                      # Git Ignore-Regeln
├── README.md                       # Diese Datei
│
├── mite_client/                    # Mite API Client
└── alphaflow_integration/          # Alphaflow Integration
```

### Logging

Für detaillierte Logs verwende `--verbose`:

```bash
python create_invoice.py --project-id 12345 --from 2024-12-01 --to 2024-12-31 --verbose
```

Oder setze in `config.yaml`:

```yaml
logging:
  level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

## Lizenz

Internes Tool für Alphaflow.

## Support

Bei Fragen oder Problemen wende dich an das Entwicklerteam.
