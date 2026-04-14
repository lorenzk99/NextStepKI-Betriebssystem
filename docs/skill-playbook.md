# Skill-Playbook

Anleitung zum Entwurf, Testen und Aktivieren neuer Skills.

## Wann braucht es einen Skill?

Ein Skill ist sinnvoll, wenn eine Aufgabe **wiederholbar** ist und klare
**Ein-/Ausgabe**, einen **Prozess** (SOP) und eine **Definition of Done** hat.
Einmalige Analysen oder Freitext-Anfragen brauchen keinen Skill.

## Quick-Start (Interview-Modus)

```bash
nextstep-os chat "Erstelle einen neuen Skill für <Aufgabe>"
```

Der Meta-Skill `neuen-skill-erstellen` führt dich durch:

1. Briefing-Interview
2. Governance-Parameter (Ampel, Modus, HIL-Gates)
3. SOP-Entwurf
4. Kontext-Mapping (Stufe 1/2/3)
5. Definition of Done
6. Activation Gate (3+ Testläufe)

## Manueller Weg

### 1. Datei anlegen

`data/skills/<slug>.md`:

```markdown
---
id: <slug>
name: <Titel>
status: Entwurf
owner: [OWNER]
ampel: 🟢 | 🟡 | 🔴
execution_mode: Strict | Search
nutzungsart: public | private
keywords: [term1, term2, ...]
beschreibung: >
  Was macht dieser Skill in einem Satz.
eingabe:
  - Input A (Pflicht)
  - Input B (optional)
ausgabe:
  - Output X
context:
  stufe_1_kern:
    - governance/handbuch.md
  stufe_2_aufgabe: []
  stufe_3_hintergrund: []
update_quellen:
  - data/feedback/entries/
---

## 🚦 Governance
<Ampel-Begründung>

## 📋 Startprotokoll
<Was muss vor Start geprüft werden?>

## 🔧 Arbeitsanweisung (SOP)
1. ...
2. ...

## ✅ Definition of Done
- ✅ ...
- 🚫 ...

## 📝 Learnings
<!-- Silent-Patch-Log -->
```

### 2. Im Register eintragen

`data/skills/_index.yaml`:

```yaml
skills:
  - id: <slug>
    name: <Titel>
    path: skills/<slug>.md
    status: Entwurf
    owner: "[OWNER]"
    ampel: "🟡"
    execution_mode: Strict
    nutzungsart: public
    keywords: [term1, term2]
    beschreibung: >
      ...
```

### 3. Test (Activation Gate)

Führe **mindestens 3 Testläufe** durch:

```bash
nextstep-os chat "<realistische Anfrage, die den Skill triggert>"
```

Bewertungs-Kriterien pro Lauf:
- ✅ Skill wurde korrekt gematcht
- ✅ Kontext wurde vollständig geladen
- ✅ Output entspricht der DoD
- ✅ HIL-Gates funktionieren

### 4. Aktivieren

Setze `status: Aktiv` sowohl im Frontmatter als auch im Register.

## Governance-Kategorien

| Ampel | Wer entscheidet? | Wann einsetzen?                                 |
| ----- | ---------------- | ----------------------------------------------- |
| 🟢    | Agent autonom    | Rein interne Aufgaben, reversibel               |
| 🟡    | Mensch reviewt   | Externer Output, Kundenkontakt, Rechtliches     |
| 🔴    | Nur Mensch       | Irreversibel, vertraglich, strategisch          |

## HIL-Marker (⏸️)

Setze `⏸️` an SOP-Stellen, an denen der Agent stoppen und den Nutzer
einbeziehen muss. Klassen:

- **Approval Gate:** Freigabe vor Fortsetzung
- **Input Gate:** Rückfrage / Klärung
- **Review Gate:** Output-Prüfung vor Finalisierung

Die Governance-Engine erkennt diese Marker und blockt die Ausführung.

## Feedback-Mechanismen

Wenn ein Skill verbessert werden soll:

```bash
nextstep-os feedback record "SOP verwirrend" \
  --typ verbesserungs-idee \
  --skill-id angebot-erstellen \
  --learning "Schritt 3 sollte vor Schritt 2 stehen." \
  --patch
```

`--patch` hängt das Learning direkt an die `## 📝 Learnings`-Sektion der
Skill-MD an. Ohne `--patch` landet das Feedback nur in der DB.

## Do's & Don'ts

✅ Kurz und konkret (SOP < 15 Schritte)
✅ Eingabe/Ausgabe explizit dokumentieren
✅ HIL-Gates bei allen externen Outputs
✅ Keywords großzügig, aber fokussiert
✅ Learnings regelmäßig sichten (Monthly Review)

🚫 Keine Skills für einmalige Aufgaben
🚫 Kein Vermischen verschiedener Workflows in einem Skill
🚫 Keine „kann alles“-Mega-Skills
🚫 Kein 🟢 ohne DoD-Validierung
