---
id: tages-shutdown
name: Tages-Shutdown & Sprint-Prep
status: Aktiv
owner: "[OWNER]"
ampel: "🟢"
execution_mode: Strict
nutzungsart: private
keywords:
  - shutdown
  - tagesabschluss
  - sprint
  - tagesplan
  - morgen planen
  - tages rückblick
  - daily review
  - briefing
beschreibung: >
  Tagesabschluss mit Rückblick, Sprint-Plan für morgen, Diktat & Delegation,
  Archivierung in Briefing-Datenbank.
eingabe:
  - Aktueller Tag (implizit)
  - Diktat-Input vom User (frei)
ausgabe:
  - Tages-Rückblick (erledigte vs. offene Tasks, Pipeline-Updates, Content-Status)
  - Sprint-Plan für morgen (3 High-Impact-Aufgaben mit Zeitslots)
  - Erstellte Artefakte aus Diktat (Tasks, E-Mail-Drafts, Meeting-Briefs)
  - Briefing-Eintrag im Archiv
context:
  stufe_1_kern:
    - governance/handbuch.md
    - context/personal/prioritaeten-und-ziele.md
    - context/personal/rollenprofil.md
  stufe_2_aufgabe:
    # Kalender (heute + morgen), Task-Liste, Pipeline-Status, Content-Plan
  stufe_3_hintergrund:
    # Die letzten 3–5 Briefings (Compound Context für offene Loops)
update_quellen:
  - data/feedback/entries/
---

## 🚦 Governance
🟢 GRÜN – Vollständig autonom, privater Output für den Nutzer selbst.

## 📋 Startprotokoll
1. Lade den heutigen Kalender (erledigte Meetings + Stichworte).
2. Lade die offene Task-Liste.
3. Lade den Pipeline-Status (Deals, Kundenprojekte).
4. Lade den aktuellen Content-Plan (falls relevant).
5. Lade die letzten 3–5 Briefings als Compound Context — offene Loops erkennen.

## 🔧 Arbeitsanweisung (SOP)

### Phase 1: Tages-Rückblick
Strukturiere den heutigen Tag:
- **Erledigte Tasks** — aus Task-Liste (Status: heute fertig)
- **Offene Tasks** — was ist liegen geblieben? Warum?
- **Pipeline-Updates** — neue Deals? Status-Änderungen?
- **Content-Status** — geplant / live / verschoben?
- **Highlights** — was lief besonders gut?
- **Lowlights** — was lief nicht wie geplant?

### Phase 2: Sprint-Plan für morgen
Basierend auf:
- Den offenen Tasks aus Phase 1
- Dem morgigen Kalender (freie Blöcke)
- Der aktuellen #1 Priorität (siehe `context/personal/prioritaeten-und-ziele.md`)

Plane **3 High-Impact-Aufgaben** mit konkreten Zeitslots:
1. **[09:00–10:30]** — [Aufgabe 1]
2. **[11:00–12:00]** — [Aufgabe 2]
3. **[14:00–15:30]** — [Aufgabe 3]

Nicht mehr als 3, sonst wird's unrealistisch.

### Phase 3: Diktat & Delegation
Frage den User: **"Was willst du noch loswerden?"**

User diktiert frei. Du setzt um:
- **Tasks** erstellen (in Task-Liste)
- **E-Mail-Drafts** schreiben (als Platzhalter-Block mit Empfänger/Betreff/Entwurf)
- **Meeting-Briefs** erstellen (für morgige Termine)
- **Andere Skills** ausführen (z.B. "Erstelle Angebot" → Skill `angebot-erstellen` triggern)

⏸️ **INPUT GATE:** User diktiert. Warte auf "fertig" oder gleichwertiges Signal.

### Phase 4: Briefing archivieren
Speichere einen Briefing-Eintrag mit:
- Datum
- Tages-Rückblick (Phase 1)
- Sprint-Plan (Phase 2)
- Erstellte Artefakte (Phase 3)
- Offene Loops / unerledigte Punkte

Ort: `data/meetings/briefings/YYYY-MM-DD.md` (Briefings-Archiv).

Dieses Archiv ist ab morgen wieder verfügbar als Stufe-3-Kontext — so erkennt der Skill wiederkehrende Muster.

## ✅ Definition of Done

- ✅ Alle 4 Phasen durchlaufen
- ✅ Sprint-Plan für morgen ist realistisch (keine 12h-Blöcke, freie Puffer)
- ✅ Alle Diktate in Artefakte überführt (keine offenen Punkte aus dem Diktat)
- ✅ Briefing-Eintrag ist archiviert und von morgen aus abrufbar

### No-Gos
- 🚫 Sprint-Plan mit mehr als 3 High-Impact-Aufgaben (unrealistisch)
- 🚫 Diktat nicht in konkrete Artefakte überführt
- 🚫 Briefing ohne Datum oder ohne Sprint-Plan
- 🚫 Offene Loops nicht benannt

## 📝 Learnings
<!-- Silent-Patch-Log, chronologisch. Format: YYYY-MM-DD – Kurzsatz -->
