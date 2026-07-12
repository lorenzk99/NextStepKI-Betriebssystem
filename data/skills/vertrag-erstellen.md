---
id: vertrag-erstellen
name: Vertrag erstellen
status: Aktiv
owner: "Lorenz Kopp"
ampel: "🔴"
execution_mode: Strict
nutzungsart: public
keywords:
  - vertrag
  - vertrag erstellen
  - vertrag schreiben
  - vertragsentwurf
  - saas vertrag
  - vermittlungsvertrag
  - kundenvertrag
  - contract
  - vertragserstellung
  - av vertrag
beschreibung: >
  Erstellt einen Vertragsentwurf für NextStepHR-Kunden (SaaS-Vertrag,
  Vermittlungsvertrag, AV-Vertrag) auf Basis der Kundendaten und der
  Standard-Konditionen. Rechtlich sensibel — immer Review durch Lorenz,
  bei neuen Klauseln juristische Prüfung.
eingabe:
  - Vertragstyp (Pflicht) — SaaS / Vermittlung / AV-Vertrag / Sonstiges
  - Kundendaten (Pflicht) — Firmenname, Rechtsform, Anschrift, Vertretungsberechtigte(r)
  - Konditionen (Pflicht) — Budget/Prozentsatz, Laufzeit, Startdatum
  - Bestehende Vertragsvorlage (optional, empfohlen)
  - Sonderabsprachen aus dem Verkaufsgespräch (optional)
ausgabe:
  - Vollständiger Vertragsentwurf mit allen Pflichtangaben
  - Liste aller Stellen mit "[PRÜFEN]"-Markierung
  - Checkliste für den Review (was muss Lorenz verifizieren?)
context:
  stufe_1_kern:
    - governance/handbuch.md
    - context/personal/firmenprofil.md
  stufe_2_aufgabe:
    # zur Laufzeit: Vertragsvorlage aus context/sources/, Kundendaten
  stufe_3_hintergrund:
    # Archiv: bisherige Verträge als Referenz
update_quellen:
  - data/feedback/entries/
---

## 🚦 Governance
🔴 ROT – Verträge sind rechtlich bindend. Der Entwurf wird IMMER von Lorenz geprüft. Neue oder geänderte Klauseln (abweichend von der Vorlage) erfordern juristische Prüfung, bevor sie verwendet werden. Kein Versand, keine Unterschrift, keine Zusage durch die KI.

## 📋 Startprotokoll
1. Prüfe, ob Vertragstyp, Kundendaten und Konditionen vollständig vorliegen.
2. Fehlt etwas Wesentliches: ⏸️ INPUT GATE — konkrete Liste der fehlenden Angaben ausgeben und stoppen.
3. Prüfe, ob eine Vertragsvorlage in `context/sources/` existiert. Falls ja: Vorlage ist die Basis, keine freie Neuformulierung.
4. Falls keine Vorlage existiert: explizit darauf hinweisen, dass der Entwurf ohne geprüfte Vorlage entsteht und vollständig juristisch geprüft werden muss.

## 🔧 Arbeitsanweisung (SOP)

### 1. Vertragstyp und Standard-Konditionen bestimmen
NextStepHR-Standardmodelle:
- **SaaS-Vertrag:** 25 % des eingesetzten Recruiting-Budgets pro Monat
- **Vermittlungsvertrag:** 18 % des Bruttojahresgehalts bei erfolgreichem Hire
- **AV-Vertrag (Auftragsverarbeitung):** DSGVO-Pflicht bei SaaS-Kunden — immer zusammen mit dem SaaS-Vertrag anbieten

Weichen die Konditionen vom Standard ab → Abweichung deutlich markieren: `[PRÜFEN: Abweichung vom Standard — 20 % statt 25 %]`.

### 2. Pflichtangaben zusammenstellen
- Vollständige Parteienbezeichnung (Firmenname, Rechtsform, Anschrift, Vertretung)
- Vertragsgegenstand (präzise Leistungsbeschreibung)
- Vergütung inkl. Fälligkeit, Zahlungsweise, MwSt.-Hinweis
- Laufzeit, Kündigungsfristen, Verlängerungsregel
- Datum, Unterschriftenfelder beider Parteien

Fehlende Angaben NIEMALS erfinden — als `[PRÜFEN: fehlt — bitte ergänzen]` markieren.

### 3. Entwurf schreiben
- Vorlage als Basis verwenden, nur die variablen Felder befüllen
- Ohne Vorlage: klare, verständliche Struktur (Präambel, §-Gliederung, Schlussbestimmungen)
- Sprache: präzise, keine Füllfloskeln, keine amerikanischen Vertragsmuster-Übersetzungen
- Sonderabsprachen aus dem Verkaufsgespräch als eigenen Paragraphen aufnehmen und markieren: `[PRÜFEN: Sonderabsprache aus Gespräch vom TT.MM.]`

### 4. Selbstcheck
- Alle Platzhalter befüllt oder als `[PRÜFEN]` markiert?
- Konditionen stimmen mit Eingabe überein (Zahlen doppelt prüfen)?
- Keine Klauseln erfunden, die nicht aus Vorlage oder Eingabe stammen?

### 5. Review-Checkliste erstellen
Am Ende des Entwurfs eine kompakte Checkliste ausgeben:
- [ ] Parteienbezeichnung korrekt (Handelsregister prüfen)
- [ ] Konditionen mit Verkaufsgespräch abgeglichen
- [ ] Alle `[PRÜFEN]`-Stellen aufgelöst
- [ ] Bei neuen Klauseln: juristische Prüfung erfolgt
- [ ] AV-Vertrag beigelegt (bei SaaS)

⏸️ **REVIEW GATE:** Entwurf geht an Lorenz. Kein weiterer Schritt ohne explizite Freigabe. Versand und Signatur erfolgen ausschließlich durch Lorenz.

## ✅ Definition of Done

- ✅ Vertragstyp korrekt und Standard-Konditionen angewendet (oder Abweichung markiert)
- ✅ Alle Pflichtangaben vorhanden oder als `[PRÜFEN]` markiert
- ✅ Keine erfundenen Daten, Zahlen oder Klauseln
- ✅ Review-Checkliste am Ende enthalten
- ✅ Sonderabsprachen dokumentiert und markiert

### No-Gos
- 🚫 Rechtsverbindliche Zusagen oder Versand durch die KI
- 🚫 Klauseln erfinden oder aus dem Internet übernehmen ohne Markierung
- 🚫 Kundendaten, Preise oder Fristen raten
- 🚫 Juristische Bewertungen abgeben ("dieser Vertrag ist rechtssicher")
- 🚫 Vorlage eigenmächtig umformulieren

## 📝 Learnings
<!-- Silent-Patch-Log, chronologisch. Format: YYYY-MM-DD – Kurzsatz -->
