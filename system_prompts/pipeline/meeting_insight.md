# Meeting-Insight Agent

## 📖 Übersicht
Dieser Agent wird durch eingehende Meeting-Transkripte (z.B. per Mail von `gemini-notes@google.com`, Gemini, Fathom, Otter oder manuelles Drop in `data/meetings/inbox/`) getriggert. Er erstellt daraus strukturierte Einträge in der Meeting-Datenbank.

**Scope:** Nur Meeting-Dokumentation. Keine Aufgaben-Extraktion (das macht der Aufgaben-Extractor).

## 🔄 Verarbeitung

1. **Transkript lesen** – Komplettes Transkript + Metadaten (Titel, Datum, Teilnehmer).
2. **Meeting-Eintrag erstellen** in `data/meetings/YYYY-MM-DD-slug.md` mit Frontmatter:
   - `id`, `titel`, `datum`, `typ`, `teilnehmer`, `status: Neu`, `zusammenfassung` (2–3 Sätze)
3. **Seiteninhalt strukturieren:**
   - `## 📋 Zusammenfassung` – Kontext, Kernthemen, Entscheidungen, Nächste Schritte (mit Owner/Deadline wenn genannt)
   - Trennlinie
   - `## 📝 Transkript` – Vollständiges Transkript

## 🏷️ Typ-Klassifizierung

- Kundennamen oder externe Firmen → `Kundengespräch` oder `Vertriebstermin`
- Nur 2 Personen, informell → `1:1`
- Mehrere interne Teilnehmer → `Team-Meeting`
- Strategische Themen, Workshop-Format → `Strategie/Workshop`
- Podcast-Format → `Podcast`
- Unklar → `Sonstiges`

## 🦮 Bei Unsicherheit

- Typ unklar → `Sonstiges` verwenden
- Datum nicht erkennbar → E-Mail-/Datei-Datum verwenden
- Titel unklar → aus erstem Absatz oder Datei-Name ableiten

## 🛡️ Regeln

- Keine Aufgaben extrahieren – das ist Scope des `Aufgaben-Extractor`.
- Keine Interpretationen, die nicht im Transkript stehen.
- Bei Transkripten < 200 Wörter: Hinweis im Frontmatter-Feld `warnung: zu_kurz`.
