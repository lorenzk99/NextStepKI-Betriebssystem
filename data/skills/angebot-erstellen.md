---
id: angebot-erstellen
name: Angebot erstellen
status: Aktiv
owner: "[OWNER]"
ampel: "🟡"
execution_mode: Strict
nutzungsart: public
keywords:
  - angebot
  - offer
  - proposal
  - kundenangebot
  - angebot schreiben
  - angebot erstellen
  - preisangebot
beschreibung: >
  Erstellt eine vollständige Angebotsseite auf Basis eines Kundenbriefings.
  Analysiert den Bedarf, definiert die Angebotsstruktur und schreibt das
  Angebot im definierten Format.
eingabe:
  - Kundenbriefing / Erstgesprächs-Notizen (Pflicht)
  - Leistungsübersicht / Produktportfolio (Pflicht)
  - Budget-Rahmen (optional)
  - Bestehendes Angebots-Template (optional)
ausgabe:
  - Fertige Angebotsseite im definierten Format
  - Zusammenfassung der Kundenbedürfnisse
  - Nächste Schritte / Follow-up-Empfehlung
context:
  stufe_1_kern:
    - governance/handbuch.md
    # Wenn vorhanden: context/sources/angebots-template.md
  stufe_2_aufgabe:
    # wird zur Laufzeit gemappt: Kundenbriefing, Leistungsübersicht
  stufe_3_hintergrund:
    # Archiv: bisherige Angebote
update_quellen:
  - data/feedback/entries/
---

## 🚦 Governance
🟡 GELB – Output-Review durch Vertriebsverantwortlichen vor Versand.

## 📋 Startprotokoll
1. Prüfe, ob das Kundenbriefing vollständig ist (Name, Unternehmen, Bedarf).
2. Lade die aktuelle Leistungsübersicht.
3. Prüfe, ob ein Angebots-Template vorhanden und aktuell ist.
4. Falls Budget-Rahmen fehlt: entscheide basierend auf Kundensignalen im Briefing.

## 🔧 Arbeitsanweisung (SOP)

### 1. Kundenbriefing analysieren
Extrahiere:
- Bedürfnisse und Schmerzpunkte (mit Zitaten/Belegen aus dem Briefing)
- Ziele des Kunden
- Budget-Signale (explizit oder implizit)
- Zeitrahmen / Deadlines
- Entscheidungsträger

### 2. Passende Module/Pakete identifizieren
Gehe die Leistungsübersicht durch und identifiziere 2–4 Module, die zum Bedarf passen. Priorisiere nach Impact, nicht nach Umsatz.

### 3. Angebotsstruktur definieren
Standardstruktur:
1. **Einleitung** mit direktem Bezug auf das Erstgespräch
2. **Verständnis der Situation** (Ausgangslage, Herausforderungen, Ziele)
3. **Leistungsumfang** (Module/Pakete)
4. **Zeitplan** (Phasen, Meilensteine)
5. **Investment** (Transparente Aufschlüsselung)
6. **Nächste Schritte**

### 4. Angebot schreiben
- **Einleitung** nimmt direkten Bezug auf das Gespräch (kein Copy-Paste-Einstieg)
- **Leistungsumfang** beschreibt für jedes Modul: Was + Warum relevant für diesen Kunden + Outcome
- **Zeitplan** mit realistischen Phasen
- **Investment** mit klarer Gliederung (Module/Phasen)
- **Nächste Schritte** mit konkretem Call-to-Action

Sprache: Kommunikationsstil des Nutzers beachten (siehe persönlicher Kontext).
**Keine generischen Textbausteine.**

### 5. Preiskalkulation einfügen
- Transparente Aufschlüsselung nach Modulen/Phasen
- Keine erfundenen Zahlen — wenn Preise unklar, markiere `[PREIS PRÜFEN: ...]`
- Summenbildung + MwSt.-Hinweis

### 6. Qualitätscheck
Prüfe gegen die DoD (siehe unten). Korrigiere alles, was nicht erfüllt ist.

⏸️ **REVIEW GATE:** Zeige die fertige Angebotsseite dem Vertriebsverantwortlichen. Preise bestätigen lassen. Persönliche Anpassungen vornehmen.

### 7. Finale Version erstellen
Nach Review: finale Version für Versand vorbereiten (ggf. als PDF exportieren, als E-Mail-Draft, oder auf die Kundenseite verlinken).

## ✅ Definition of Done

- ✅ Alle Abschnitte ausgefüllt (Einleitung, Situation, Leistungsumfang, Zeitplan, Investment, Nächste Schritte)
- ✅ Konkreter Bezug auf das Erstgespräch (mind. 2 Zitate/Referenzen)
- ✅ Preise vollständig aufgeschlüsselt und transparent
- ✅ Keine generischen Textbausteine — alles kundenspezifisch
- ✅ Format entspricht der Angebotsvorlage
- ✅ Kommunikationsstil stimmt mit `context/personal/kommunikationsstil.md` überein

### No-Gos
- 🚫 Preise ohne Rücksprache mit Vertrieb erfinden
- 🚫 Leistungen versprechen, die nicht im Portfolio sind
- 🚫 Generische Einleitung ohne Bezug auf den Kunden
- 🚫 Angebot ohne klaren Call-to-Action

## 📝 Learnings
<!-- Silent-Patch-Log, chronologisch. Format: YYYY-MM-DD – Kurzsatz -->
