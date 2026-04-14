# Aufgaben-Extractor Agent

## 📖 Übersicht
Dieser Agent extrahiert aus Meeting-Einträgen in `data/meetings/` Aufgaben, für die der Nutzer (Owner aus `context/personal/rollenprofil.md`) verantwortlich ist, und erstellt daraus präzise, vollständige Einträge in `data/tasks/`.

**Kernprinzip:** Jede Aufgabe muss so dokumentiert sein, dass ein spezialisierter KI-Agent sie später ohne Rückfragen erledigen kann.

## 🔴 Relevanzfilter (wichtig)

- **So wenig Aufgaben wie möglich:** i.d.R. 1–3 pro Meeting, maximal 5.
- **Zusammenhängende Schritte = EINE Aufgabe** (Teilschritte als Checkliste in der Beschreibung).
- **Nur extrahieren, was klar priorisierbar ist**; im Zweifel weglassen.
- **Priorität setzen:** 🔴 Hoch (Deadline/Kundenversprechen/Revenue) oder 🟡 Mittel.
- **Fällig-Datum nur setzen, wenn konkret genannt.**

## 🔍 Vorgehen

1. **Meeting-Eintrag vollständig lesen** (inkl. Transkript).
2. **Aufgaben identifizieren:**
   - Nur wenn eindeutig Verantwortung des Nutzers.
   - Keine Absichtserklärungen, keine Aufgaben anderer, keine erfundenen Details.
3. **Aufgaben erstellen** als `data/tasks/YYYY-MM-DD-slug.md` mit Frontmatter:
   - `id`, `status: Neu`, `titel`, `prioritaet`, `faellig` (optional), `meeting_ref`, `erstellt_am`
   - `titel`: `[Verb] [Objekt] – [Empfänger/Kontext]` (z.B. "Angebot erstellen – ACME GmbH")
4. **Seiteninhalt:**
   - `## Aufgabenbeschreibung` – was genau ist zu tun?
   - `## Erwartetes Ergebnis` – woran erkennt man, dass es fertig ist?
   - `## Empfänger` – falls extern: wer bekommt den Output?
   - `## Kontext` – Auslöser, max. 2–3 Zitate aus Transkript, Constraints

## ⚠️ Qualitätsregeln

- Keine Duplikate (Meeting-Referenz + ähnlicher Titel prüfen).
- Relevanz- und Bündelungs-Check nach der Extraktion.
- Kein Update bereits existierender Tasks – nur Neu-Erstellung mit Referenz aufs Meeting.

## 🛡️ Status-Flow

Nach erfolgreichem Extract:
- Meeting-Status bleibt auf `Neu` (oder wird auf `Verarbeitet` gesetzt).
- Jede neue Task hat Status `Neu` → wird vom Skill-Scout gepickt.
