---
id: neuen-skill-erstellen
name: Neuen Skill erstellen
status: Aktiv
owner: "[OWNER]"
ampel: "🟡"
execution_mode: Strict
nutzungsart: public
keywords:
  - skill erstellen
  - neuen skill
  - skill bauen
  - skill entwickeln
  - create skill
  - skill anlegen
  - prozess dokumentieren
  - sop erstellen
beschreibung: >
  Meta-Skill: Erstellt neue Skills im System via strukturiertem Interview.
  Führt durch Briefing, Governance, SOP, Kontext-Mapping, DoD und
  Activation Gate.
eingabe:
  - Freie Beschreibung, was der Skill tun soll (Pflicht)
  - Skill-Owner (Pflicht)
  - Bestehender Prozess (optional)
  - Beispiel-Durchlauf (optional)
ausgabe:
  - Vollständiger Skill-Eintrag in data/skills/{id}.md
  - Eintrag im Skill-Register data/skills/_index.yaml
  - Ggf. neue Kontext-Einträge in data/context/_index.yaml
  - Test-Run-Dokumentation
  - Status "Entwurf" (nach Testing → "Aktiv")
context:
  stufe_1_kern:
    - governance/handbuch.md
  stufe_2_aufgabe:
    - skills/_index.yaml         # bestehende Skills (Duplikat-Check)
    - context/_index.yaml        # verfügbare Kontext-Quellen
  stufe_3_hintergrund:
    - feedback/entries/          # Muster aus Skill-Erstellungs-Feedback
update_quellen:
  - data/feedback/entries/
  - data/governance/handbuch.md
  - data/skills/_index.yaml
---

## 🚦 Governance
🟡 GELB – Skill-Eintrag wird nach Erstellung vom Owner reviewed und manuell auf `Aktiv` gesetzt.

## 📋 Startprotokoll
1. Prüfe, ob `data/skills/_index.yaml` lesbar ist.
2. Prüfe, ob `data/context/_index.yaml` lesbar ist.
3. Prüfe, ob `data/governance/handbuch.md` verfügbar ist.
4. Lade die bestehenden Skills (Name + Keywords + Beschreibung) für den Duplikat-Check.

## 🔧 Arbeitsanweisung (SOP)

### 1. Freies Briefing
User beschreibt frei, was der Skill können soll. Höre zu und sammle:
- Ziel
- Input (was muss geliefert werden?)
- Output (was kommt raus?)
- Owner
- erste Keywords

⏸️ **INPUT GATE:** Warte, bis der User signalisiert, dass er fertig mit dem Briefing ist.

### 2. Rückspiegelung + Vorschlag
Fasse zusammen und liefere einen ersten Vorschlag:
- **Skill-Name** (Verb + Objekt)
- **Ziel** (1 Satz)
- **Input/Output** (Bullet Points)
- **Keywords** (5–10)
- **Nutzungsart** (Public oder Privat)
- **Execution-Modus** (Strict oder Search)

Prüfe gegen bestehende Skills — wenn ein ähnlicher Skill existiert, weise darauf hin und frage, ob der bestehende erweitert oder ein neuer angelegt werden soll.

⏸️ **APPROVAL GATE:** User bestätigt den Vorschlag oder korrigiert.

### 3. Vertiefung (optional, aber empfohlen)
Gehe systematisch durch:
- **Gap-Analyse:** Welche impliziten Schritte sind im Prozess, die noch nicht dokumentiert sind?
- **Entscheidungspunkte:** Wo muss der Skill Verzweigungen berücksichtigen?
- **Golden Sample:** Bitte um 1 konkretes Beispiel eines guten Outputs.
- **No-Gos:** Was darf auf keinen Fall passieren?

⏸️ **INPUT GATE:** User liefert die gewünschten Details.

### 4. Governance-Vorschlag
Analysiere den Skill-Typ und schlage vor:
- **Ampel-Farbe** — nutze die 3 Entscheidungsfragen aus `data/governance/handbuch.md`:
  1. Worst-Case? → hoch/mittel/niedrig
  2. Direkt extern? → ja/nein
  3. Rechtliche/finanzielle Implikationen? → ja/nein
- **HIL-Punkte** — bei 🟡/🔴: wo genau?
- **Execution-Modus** — 🔒 Strict (Default) oder 🔍 Search

⏸️ **APPROVAL GATE:** User bestätigt oder überschreibt.

### 5. Arbeitsanweisung (SOP) entwickeln
- 4–10 Schritte, sequenziell
- Governance-Ampel als erste Zeile (Format: `🟡 GELB – [Kurzbegründung]`)
- HIL-Punkte mit `⏸️ APPROVAL/INPUT/REVIEW GATE:` markieren
- Jeder Schritt eine klare Aktion — KI-tauglich formuliert
- Bei Unsicherheit: lieber zu spezifisch als zu generisch

⏸️ **REVIEW GATE:** User reviewed die SOP.

### 6. Definition of Done definieren
- Positivkriterien: Woran erkennt man ein gutes Ergebnis?
- Mindestens **3 No-Gos** (Negativbeispiele/typische Fehler)
- Messbare Kriterien bevorzugen

⏸️ **APPROVAL GATE:** User bestätigt die DoD.

### 7. Kontext-Mapping
Identifiziere 3–5 Kontext-Quellen und ordne sie in die 3-Stufen-Hierarchie:
- **Stufe 1 (Kern):** immer laden — z.B. Skill-Definition selbst, Governance-Handbuch
- **Stufe 2 (Aufgabe):** situativ laden — aufgabenspezifische Quellen
- **Stufe 3 (Hintergrund):** nur auf Anfrage — Archive, Vergangenheit

**Granularitäts-Regel anwenden:**
- Quelle von mehreren Skills genutzt (oder potenziell)? → in `data/context/_index.yaml` registrieren + hier referenzieren
- Nur für diesen Skill relevant? → direkt im Frontmatter belassen

⏸️ **REVIEW GATE:** User reviewed das Mapping.

### 8. Update-Quellen definieren
Wo kommen zukünftige Learnings her?
- `data/feedback/entries/` (Default)
- Ggf. spezifische externe Quellen

### 9. Skill-Eintrag erstellen
Erstelle:
1. `data/skills/{id}.md` mit vollständigem Frontmatter + allen Sektionen
2. Eintrag in `data/skills/_index.yaml`
3. Ggf. neue Einträge in `data/context/_index.yaml`

**Read-Back-Verification:** Lies den Skill nochmals vor (Kurzfassung) und bestätige, dass alle Properties gesetzt sind.

⏸️ **REVIEW GATE:** User reviewed den finalen Skill-Eintrag.

### 10. Activation Gate
- Führe **3–5 Testläufe** mit realistischen Inputs durch
- Prüfe jedes Ergebnis gegen die DoD
- Dokumentiere Abweichungen und patche den Skill entsprechend
- Wenn alle Testläufe bestehen → Status auf `Aktiv` setzen

⏸️ **APPROVAL GATE:** Owner gibt den Skill frei.

## ✅ Definition of Done

### Skill-Eintrag (Properties vollständig)
- ✅ Alle Frontmatter-Properties ausgefüllt (keine leeren Felder)
- ✅ Arbeitsanweisung: 4–10 Schritte, so spezifisch, dass ein KI-Agent die Aufgabe fehlerfrei ausführen kann
- ✅ Governance-Ampel als erste Zeile der SOP
- ✅ Kontext Stufe 1–2: valide Quellen-Referenzen (Pfade existieren)
- ✅ Keywords: 5–10 für Skill-Selection

### Kontext-Datenbank
- ✅ Mindestens 1 Kontext-Quelle verlinkt
- ✅ Granularitäts-Regel angewendet (geteilt → `_index.yaml`, skill-spezifisch → Frontmatter)

### Activation Gate
- ✅ 3–5 Testläufe mit realistischen Inputs bestanden
- ✅ Output gegen DoD geprüft

### No-Gos
- 🚫 Multi-Purpose Skills (mehrere unterschiedliche Outputs in einem Skill)
- 🚫 Kontext-Quellen als Plaintext im Skill kopieren (müssen Referenzen sein)
- 🚫 Skill ohne Definition of Done aktivieren
- 🚫 HIL-Punkte bei 🟡/🔴 Skills fehlen

## 📝 Learnings
<!-- Silent-Patch-Log, chronologisch. Format: YYYY-MM-DD – Kurzsatz -->
