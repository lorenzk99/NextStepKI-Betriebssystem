# Governance-Handbuch

> **Single Source of Truth** für alle Governance-Regeln des NextStepKI KI-Betriebssystems. Jeder Skill referenziert dieses Dokument als Kern-Kontext (Stufe 1).

Dieses Handbuch definiert **wie viel Autonomie** ein Agent hat — nicht **was** er tut (das regeln die Skills).

---

## 1. Ampel-System

Jede SOP beginnt mit einer Governance-Ampel als erste Zeile.

| Ampel | Bedeutung | Agent-Autonomie | HIL-Pflicht | Typische Aufgaben |
|---|---|---|---|---|
| 🟢 GRÜN | Vollständig autonom | Input → Output ohne Pause | Keine | Meeting-Zusammenfassung, Daten-Formatierung, interne Reports |
| 🟡 GELB | Agent bereitet vor, Mensch reviewed | Entwurf erstellen, dann pausieren | Mind. 1 Review Gate | Kundenangebote, Blog-Artikel, externe Dokumente |
| 🔴 ROT | Nur Mensch, Agent unterstützt | Nur Recherche / Vorarbeit | HIL an jedem kritischen Schritt | Verträge, Personalentscheidungen, Krisenkommunikation |

**Eskalationsregel:** Im Zweifel eine Stufe höher. Gelb statt Grün, Rot statt Gelb.

### Farb-Entscheidung in 3 Fragen

1. Was ist das Worst-Case-Szenario bei einem fehlerhaften Output? → **Hoch = 🔴 / Mittel = 🟡 / Niedrig = 🟢**
2. Geht der Output direkt an externe Stakeholder? → **Ja = mindestens 🟡**
3. Gibt es rechtliche oder finanzielle Implikationen? → **Ja = 🔴**

---

## 2. Human-in-the-Loop (HIL)

HIL-Punkte werden direkt in der SOP mit `⏸️` markiert. Drei Typen:

### ⏸️ Approval Gate
Agent pausiert und wartet auf Freigabe, bevor er weitermacht.

*Syntax in SOP:* `⏸️ APPROVAL: Warte auf Freigabe von [WAS], bevor du [NÄCHSTER SCHRITT] startest.`

### ⏸️ Input Gate
Agent braucht zusätzliche Information vom Menschen.

*Syntax in SOP:* `⏸️ INPUT: Frage nach [WAS] – benötigt für [WARUM].`

### ⏸️ Review Gate
Agent liefert Output, Mensch prüft und gibt Feedback.

*Syntax in SOP:* `⏸️ REVIEW: Zeige [OUTPUT] und warte auf Feedback.`

### HIL-Regeln

- 🟢 GRÜN: **0 HIL-Punkte** (sonst ist der Skill nicht grün)
- 🟡 GELB: **Mindestens 1 Review Gate** (am Ende)
- 🔴 ROT: **HIL an jedem Entscheidungspunkt**
- HIL-Punkte sind **nicht optional** — der Agent MUSS pausieren

---

## 3. Execution-Modi

### 🔒 Strict Mode (Default)
- Agent arbeitet **nur** mit dem verlinkten Kontext (Stufe 1–3)
- Kein Enterprise Search, keine externe Recherche
- Maximale Kontrolle und Reproduzierbarkeit
- **Standard für alle neuen Skills**

### 🔍 Search Mode (Opt-in)
- Enterprise Search / Web-Search erlaubt
- Guard Rails aktiv:
  - Aktualitäts-Filter bei Duplikaten
  - Quellen-Transparenz im Output (Footnotes, URL-Liste)
  - Quellen-Hierarchie bleibt bestehen
- Nur aktivieren, wenn der Skill aktive Recherche braucht

### Quellen-Hierarchie (bei Widersprüchen)

1. **Skill-Anweisung (SOP)** – höchste Priorität
2. **Verlinkter Kontext** (Stufe 1 > Stufe 2 > Stufe 3)
3. **Enterprise Search** – niedrigste Priorität

---

## 4. Activation Gate

Kein Skill geht produktiv ohne Activation Gate. Checkliste:

- [ ] Alle Properties vollständig ausgefüllt
- [ ] SOP: 4–10 Schritte, KI-tauglich formuliert
- [ ] Governance-Ampel als erste Zeile der SOP
- [ ] HIL-Punkte gesetzt (wenn Gelb/Rot)
- [ ] Execution-Modus definiert
- [ ] Kontext-Mapping abgeschlossen
- [ ] Definition of Done klar und messbar
- [ ] 3–5 Testläufe mit realistischen Inputs bestanden
- [ ] Feedback aus Testläufen eingearbeitet

### Testlauf-Protokoll

1. Mindestens 3 verschiedene Inputs verwenden
2. Ergebnisse gegen die DoD prüfen
3. Abweichungen dokumentieren
4. Skill-Patch erstellen (SOP oder Kontext anpassen)
5. Erneut testen bis Gate bestanden

---

## 5. Sondersituationen

### Ampel-Upgrade / Downgrade
- **Upgrade (🟡 → 🟢):** Nur nach 10+ erfolgreichen Runs ohne Korrekturen
- **Downgrade (🟢 → 🟡):** Sofort bei einem kritischen Fehler
- Jede Änderung wird dokumentiert (Feedback-Datenbank)

### Neue Teammitglieder
- Starten mit 🟡 GELB für alle Skills (auch wenn der Skill 🟢 GRÜN ist)
- Nach Einarbeitung (5+ Reviews) auf die Standard-Ampel umstellen

### Edge Cases
- Skill fällt in keine klare Kategorie? → 🟡 GELB als Default
- Unsicher über Execution-Modus? → 🔒 Strict als Default
- Mehrere Outputs pro Skill? → Skill aufteilen (1 Skill = 1 Output)

---

## 6. Datenklassifizierung

| Klasse | Beschreibung | KI-Verarbeitung | Beispiele |
|---|---|---|---|
| 🟢 Öffentlich | Frei verfügbare Informationen | Uneingeschränkt erlaubt | Website-Inhalte, Blog-Artikel |
| 🟡 Intern | Nur für Mitarbeiter bestimmt | Erlaubt mit Kontext-Isolation | Prozesse, Meeting-Notizen |
| 🟠 Vertraulich | Geschäftskritisch | Nur mit 🟡 GELB oder 🔴 ROT | Kundendaten, Finanzzahlen, Verträge |
| 🔴 Streng vertraulich | Höchste Schutzstufe | Nicht KI-verarbeitbar oder nur mit 🔴 ROT + expliziter Freigabe | Passwörter, HR-Daten, Geschäftsgeheimnisse |

### Regeln
- Jeder Skill definiert, welche Datenklassen er verarbeitet — im Kontext-Mapping dokumentieren
- Daten der Klasse 🔴 dürfen NICHT in Prompts, Kontext oder Skill-Outputs erscheinen — es sei denn, die Organisation hat eine explizite Freigabe erteilt
- Bei Unsicherheit: eine Klasse höher einstufen
- `[EIGENE REGELN ERGÄNZEN: z.B. branchenspezifische Vorschriften]`

---

## 7. Output-Richtlinien

### Kennzeichnungspflicht
- [ ] KI-generierte Inhalte werden als solche gekennzeichnet, wenn sie extern gehen
- [ ] Interne KI-Outputs müssen nicht gekennzeichnet werden, sofern ein Mensch sie reviewed hat (🟡 GELB)
- [ ] `[EIGENE KENNZEICHNUNGSREGELN ERGÄNZEN]`

### Faktenprüfung
- [ ] Outputs mit Zahlen, Statistiken oder Faktenbehauptungen werden gegen Primärquellen geprüft
- [ ] Bei 🟢 GRÜN-Skills: Faktenprüfung ist in die DoD integriert (automatisch)
- [ ] Bei 🟡 GELB-Skills: Faktenprüfung ist Teil des menschlichen Reviews
- [ ] Keine ungeprüften Zahlen in externen Dokumenten

### Formatstandards
- Alle Outputs folgen den im Skill definierten Format-Vorgaben
- Marken- und CI-konforme Sprache bei externen Outputs
- `[EIGENE FORMATREGELN ERGÄNZEN: z.B. Sprache, Tonalität, Template-Nutzung]`

### Quellentransparenz
- Wenn ein Skill im Search Mode arbeitet, werden genutzte Quellen im Output dokumentiert
- Bei Widersprüchen zwischen Quellen: explizit darauf hinweisen, nicht stillschweigend eine wählen

---

## 8. Sicherheits-Guardrails (systemisch)

Diese Regeln greifen architektonisch durch das Systemdesign:

- [ ] **🔒 Keine autonomen externen Aktionen** — Das System kann nicht eigenständig E-Mails versenden, Verträge unterschreiben oder Daten publizieren. Jede nach außen gerichtete Aktion erfordert einen menschlichen Trigger.
- [ ] **🛡️ Prompt-Injection-Schutz** — Skills sind geschlossene Systeme. Externe Inhalte (Kundendaten, E-Mails) können SOP-Anweisungen nicht überschreiben.
- [ ] **🔗 Kontext-Isolation** — Agents sehen nur den Kontext, der ihnen explizit zugewiesen wurde.
- [ ] **📋 Audit-Trail** — Jede Skill-Ausführung ist nachvollziehbar (Learnings-Logs, Feedback-Einträge, Skill-Patches).
- [ ] **⏸️ Human-in-the-Loop by Design** — Gelbe und rote Skills haben Pflicht-Stopps, die nicht übersprungen werden können.
- [ ] **🚫 Keine Selbstmodifikation** — Agents können ihre eigenen System-Anweisungen und Governance-Regeln nicht verändern. Skill-Patches werden vorgeschlagen, aber vom Skill Owner bestätigt.
- [ ] **📦 Quellen-Hierarchie** — Bei Widersprüchen: Skill-Anweisung > verlinkter Kontext > Enterprise Search.
- [ ] **🧪 Activation Gate als Pflicht** — Kein Skill geht ungetestet produktiv.
- [ ] **👤 Owner-Prinzip** — Jeder Skill und jeder Agent hat einen verantwortlichen Menschen.
- [ ] **🔄 Systematische Fehlerkorrektur** — Fehler fließen über die Lernschleife strukturiert zurück.

---

## 9. KI-Anbieter & Datenverarbeitung

Bevor ein KI-Anbieter produktiv eingesetzt wird, müssen folgende Punkte geregelt sein:

- [ ] **Kein Training mit deinen Daten** — Schriftliche Bestätigung, dass Inputs/Outputs nicht zum Modell-Training genutzt werden
- [ ] **Auftragsverarbeitungsvertrag (AVV/DPA)** — Gültiger AVV gemäß DSGVO Art. 28
- [ ] **Datenverarbeitung in der EU** — oder angemessenes Datenschutzniveau gemäß DSGVO
- [ ] **Speicherfristen definiert** — Wie lange speichert der Anbieter Prompts, Outputs, Konversationsdaten?
- [ ] **Datenlöschung gewährleistet** — Right to Erasure auf Anfrage
- [ ] **Zugriffsrechte geklärt** — Welche Mitarbeiter haben Zugriff, welche Datenklassen dürfen sie verarbeiten?
- [ ] **Sub-Prozessoren transparent** — Der Anbieter legt Drittanbieter offen
- [ ] `[EIGENE ANFORDERUNGEN: ISO 27001, SOC 2, branchenspezifische Zertifizierungen]`

---

## 10. Verantwortlichkeiten & Review-Rhythmus

### Rollen

| Rolle | Verantwortung |
|---|---|
| **Governance Owner** | Pflegt dieses Handbuch, entscheidet über Grundsatzfragen, führt Quartals-Review durch |
| **Skill Owner** | Verantwortet Ampel-Farbe, HIL-Punkte und Activation Gate für eigene Skills |
| **Agent Owner** | Verantwortet Agent-Konfiguration, Kontext-Zugriffe und Berechtigungen |
| **Reviewer** | Prüft Outputs bei 🟡 GELB-Skills, gibt Feedback |

### Review-Rhythmus

- **Wöchentlich:** Skill Owner prüft Feedback auf eigene Skills
- **Monatlich:** Governance Owner reviewed Ampel-Verteilung + offene Feedbacks (→ `nextstep-os review`)
- **Quartalsweise:** Governance-Handbuch selbst reviewen — Regeln noch aktuell? Neue Datenklassen? Neue Compliance-Anforderungen?
- **Ad hoc:** Bei Vorfällen (kritischer Fehler, Datenschutz-Incident) → sofortiger Review + ggf. Downgrade

### Änderungsprotokoll
Jede Änderung am Governance-Handbuch wird dokumentiert (Datum + Wer + Was + Warum):

```
[YYYY-MM-DD] – [NAME] – [ÄNDERUNG] – [GRUND]
```

---

*Letzte Aktualisierung: [DATUM EINSETZEN]*
*Governance Owner: [NAME EINSETZEN]*
