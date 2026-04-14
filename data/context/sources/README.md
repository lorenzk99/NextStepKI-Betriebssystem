# Geteilte Wissensquellen

Hier landen alle **geteilten Quellen**, die von mehreren Skills genutzt werden — z.B. Angebots-Templates, Tone-of-Voice-Guides, Produktübersichten.

## Granularitäts-Regel

- Wird eine Quelle von **mehr als einem Skill** gebraucht? → hier ablegen + in `data/context/_index.yaml` registrieren
- Nur von **einem Skill** gebraucht? → direkt als Referenz im Skill-Frontmatter belassen

## Quelle hinzufügen

1. Datei hier anlegen (z.B. `angebots-template.md`)
2. Eintrag in `data/context/_index.yaml` ergänzen mit:
   - `id`, `name`, `path`, `typ`, `kontext_stufe`, `token_schaetzung`, `status`, `tags`
   - `skills: [skill-id-1, skill-id-2]` — welche Skills nutzen sie?
3. In den betroffenen Skills auf die Quelle verweisen (Frontmatter `context.stufe_1_kern` etc.)

## Quellen-Typen

| Typ | Beschreibung | Aktualisierung |
|---|---|---|
| `dokument` | Statisches MD, Google Doc, PDF | Selten |
| `datenbank` | Verzeichnis mit vielen Einträgen | Laufend |
| `webseite` | Externe URL | On-Demand |
| `personen_kontext` | Stil-/Tonalitäts-Guide | Bei Bedarf |
| `api` | Externe Datenquelle via Connector | Echtzeit |
