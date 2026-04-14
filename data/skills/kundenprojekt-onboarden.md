---
id: kundenprojekt-onboarden
name: Kundenprojekt onboarden
status: Aktiv
owner: "[OWNER]"
ampel: "🟢"
execution_mode: Strict
nutzungsart: public
keywords:
  - projekt
  - onboarding
  - kickoff
  - kundenprojekt
  - projekt aufsetzen
  - projekt starten
  - stakeholder map
beschreibung: >
  Setzt ein neues Kundenprojekt vollständig auf: Kickoff vorbereiten,
  Projektseite anlegen, Stakeholder-Map erstellen, Kommunikationsplan
  definieren.
eingabe:
  - Vertragsdaten / Angebotsdokument (Pflicht)
  - Ansprechpartner beim Kunden (Pflicht)
  - Projektumfang und Zeitrahmen (Pflicht)
  - Interne Ressourcen / Teamzuordnung (optional)
ausgabe:
  - Vollständige Projektseite mit allen Abschnitten
  - Stakeholder-Map (intern + extern)
  - Kommunikationsplan (Regeltermine, Kanäle, Eskalation)
  - Kickoff-Agenda
context:
  stufe_1_kern:
    - governance/handbuch.md
    # Wenn vorhanden: context/sources/projekt-template.md
  stufe_2_aufgabe:
    - context/personal/team-kontext.md   # für Team-Zuordnung
  stufe_3_hintergrund:
    # context/sources/projekt-archiv/
update_quellen:
  - data/feedback/entries/
---

## 🚦 Governance
🟢 GRÜN – Vollständig autonom. Output ist intern und leicht korrigierbar.

## 📋 Startprotokoll
1. Prüfe, ob Vertragsdaten / Angebotsdokument vollständig sind (Projektumfang, Meilensteine, Lieferobjekte).
2. Prüfe, ob Ansprechpartner (Name + Rolle + Kontakt) beim Kunden dokumentiert sind.
3. Lade den Team-Kontext für die interne Ressourcenzuordnung.
4. Prüfe, ob ein Projekt-Template verfügbar ist.

## 🔧 Arbeitsanweisung (SOP)

### 1. Vertragsdaten analysieren
Extrahiere aus Vertrag/Angebot:
- **Projektumfang** (was wird geliefert?)
- **Meilensteine** mit Datum
- **Lieferobjekte** (Deliverables)
- **Budget** / Investment
- **Start- und Enddatum**

### 2. Projektseite anlegen
Struktur nach Template:
- **Übersicht** (Projektname, Kunde, Laufzeit, Budget, Status)
- **Stakeholder** (intern + extern)
- **Zeitplan** (Phasen, Meilensteine)
- **Kommunikation** (Regeltermine, Kanäle, Eskalation)
- **Dokumente** (Vertrag, Angebot, Briefings)
- **Notizen** (laufende Meeting-Notizen)

### 3. Stakeholder-Map erstellen
Alle Ansprechpartner (intern + extern) mit:
- Name
- Rolle / Verantwortung
- Kontaktdaten (E-Mail, Telefon)
- Kommunikationspräferenzen (falls bekannt)
- Einbeziehungs-Trigger (wann loopt man diese Person ein?)

### 4. Kommunikationsplan definieren
- **Kickoff:** Datum, Teilnehmer, Agenda
- **Weekly Sync:** Wochentag, Uhrzeit, Teilnehmer, Format (Call/Chat/Async)
- **Monthly Review:** Datum, Teilnehmer, Format
- **Kanäle:** Welcher Kanal für welchen Zweck (E-Mail formal, Slack schnell, Call für Entscheidungen)
- **Eskalationspfade:** Wer wird bei welchen Blockern informiert?

### 5. Kickoff-Agenda vorbereiten
Standardstruktur (max. 60 Min.):
1. **Vorstellungsrunde** (5 Min.)
2. **Projektziele** (5 Min.) — Was wollen wir erreichen?
3. **Meilensteine** (10 Min.) — Der Weg dahin
4. **Arbeitsweise** (10 Min.) — Regeltermine, Kanäle, Tools
5. **Rollen & Verantwortlichkeiten** (10 Min.) — Wer macht was?
6. **Offene Fragen** (10 Min.)
7. **Nächste Schritte** (5 Min.)

Jeder Punkt mit konkretem Zeitfenster und Verantwortlichem.

### 6. Qualitätscheck
Gehe alle Abschnitte der Projektseite durch:
- Keine Platzhalter
- Keine fehlenden Kontaktdaten
- Eskalationspfade vollständig
- Kickoff-Agenda mit konkreten Zeiten

Bei 🟢 GRÜN liefere direkt aus — kein Review Gate nötig, weil intern und leicht korrigierbar.

## ✅ Definition of Done

- ✅ Projektseite vollständig angelegt (alle Abschnitte ausgefüllt)
- ✅ Stakeholder-Map mit allen Ansprechpartnern (intern + extern)
- ✅ Kommunikationsplan mit Regelterminen, Kanälen und Eskalation
- ✅ Kickoff-Agenda vorbereitet mit konkreten Zeitfenstern
- ✅ Keine Platzhalter, keine fehlenden Kontaktdaten

### No-Gos
- 🚫 Projektseite ohne Stakeholder-Map
- 🚫 Fehlende Eskalationspfade im Kommunikationsplan
- 🚫 Kickoff-Agenda ohne konkrete Zeitfenster pro Punkt
- 🚫 Ansprechpartner ohne Kontaktdaten

## 📝 Learnings
<!-- Silent-Patch-Log, chronologisch. Format: YYYY-MM-DD – Kurzsatz -->
