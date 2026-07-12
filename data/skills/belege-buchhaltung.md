---
id: belege-buchhaltung
name: Belege & Buchhaltung vorbereiten
status: Aktiv
owner: "Lorenz Kopp"
ampel: "🟡"
execution_mode: Strict
nutzungsart: private
keywords:
  - beleg
  - belege
  - buchhaltung
  - rechnung
  - rechnungen
  - quittung
  - beleg erfassen
  - belege sortieren
  - buchhaltung vorbereiten
  - kontierung
  - exist nachweis
beschreibung: >
  Bereitet Belege für die Buchhaltung vor: extrahiert die Daten aus
  Beleg-Text/Beschreibung, schlägt Kategorie und Kontierung vor,
  erstellt einen strukturierten Buchungssatz-Entwurf und prüft auf
  EXIST-Relevanz. Übertrag ins Buchhaltungstool macht Lorenz.
eingabe:
  - Beleg-Inhalt (Pflicht) — Text, Beschreibung oder extrahierte Daten des Belegs
  - Zahlungsart (optional) — Firmenkonto, Kreditkarte, privat verauslagt
  - Projekt-/Kostenstellen-Zuordnung (optional)
ausgabe:
  - Strukturierter Beleg-Datensatz (Datum, Lieferant, Betrag netto/brutto, MwSt., Kategorie)
  - Kontierungsvorschlag mit Begründung
  - EXIST-Relevanz-Hinweis (förderfähig ja/nein/prüfen)
  - Unklarheiten als explizite Rückfragen
context:
  stufe_1_kern:
    - governance/handbuch.md
    - context/personal/firmenprofil.md
  stufe_2_aufgabe:
    # zur Laufzeit: Kontenrahmen/Kategorienliste aus context/sources/
  stufe_3_hintergrund: []
update_quellen:
  - data/feedback/entries/
---

## 🚦 Governance
🟡 GELB – Kategorisierung und Buchungssatz sind Vorschläge. Lorenz prüft vor Übertrag ins Buchhaltungstool. Keine steuerliche Beratung — bei steuerlichen Zweifelsfällen an Steuerberater verweisen.

## 📋 Startprotokoll
1. Prüfe, ob der Beleg-Inhalt die Mindestdaten enthält: Datum, Aussteller, Betrag.
2. Fehlen Mindestdaten: ⏸️ INPUT GATE — konkret nachfragen (z.B. "Brutto oder netto? MwSt.-Satz?").
3. Prüfe, ob eine Kategorienliste/Kontenrahmen in `context/sources/` hinterlegt ist. Falls ja: NUR diese Kategorien verwenden.

## 🔧 Arbeitsanweisung (SOP)

### 1. Beleg-Daten extrahieren
Strukturiert erfassen:
- **Datum** (Belegdatum, nicht Zahldatum)
- **Aussteller/Lieferant** (Firma, ggf. USt-IdNr.)
- **Betrag** netto / MwSt.-Satz / brutto — Beträge nachrechnen, bei Widerspruch markieren
- **Leistungsbeschreibung** (was wurde gekauft?)
- **Zahlungsart** (falls angegeben)

### 2. Kategorie & Kontierung vorschlagen
Typische Kategorien für NextStepHR (Startup-Betrieb):
- Software & SaaS-Tools (z.B. Notion, Google Workspace, Hosting)
- Marketing & Werbung (Anzeigen, Messen, Druckmaterial)
- Reisekosten (Fahrt, Übernachtung, Verpflegungsmehraufwand)
- Bürobedarf & Ausstattung
- Fremdleistungen (Freelancer, Agenturen, Beratung)
- Bewirtung (auf 70/30-Regel hinweisen)
- Personal (Gehälter, Sozialabgaben — i.d.R. via Lohnbuchhaltung)

Vorschlag immer mit 1-Satz-Begründung. Bei Unsicherheit zwei Optionen nennen und markieren: `[PRÜFEN: Kategorie A oder B]`.

### 3. EXIST-Relevanz prüfen
- Könnte der Beleg über EXIST förderfähig/nachweisrelevant sein? (Sachausgaben, Coaching, Messen)
- Ausgabe: "EXIST: ja / nein / prüfen" mit Kurzbegründung
- Keine verbindliche Aussage — nur Hinweis für Lorenz' Nachweisführung

### 4. Buchungssatz-Entwurf ausgeben
Format:
```
Datum:       TT.MM.JJJJ
Lieferant:   ...
Netto:       ...,.. €   MwSt (XX %):  ...,.. €   Brutto: ...,.. €
Kategorie:   ...
Zahlungsart: ...
EXIST:       ja/nein/prüfen — Begründung
Notiz:       ...
```

### 5. Sammelverarbeitung
Bei mehreren Belegen in einer Anfrage: Tabelle mit einer Zeile pro Beleg + Summenzeile. Unklare Belege in separater "Rückfragen"-Sektion sammeln.

⏸️ **REVIEW GATE:** Lorenz prüft Kategorien und Beträge, dann Übertrag ins Buchhaltungstool. Kein automatischer Schreibzugriff auf das Buchhaltungssystem.

## ✅ Definition of Done

- ✅ Alle Pflichtfelder extrahiert (Datum, Lieferant, Netto/MwSt./Brutto)
- ✅ Beträge nachgerechnet, Widersprüche markiert
- ✅ Kategorie mit Begründung vorgeschlagen
- ✅ EXIST-Relevanz bewertet
- ✅ Unklarheiten als explizite Rückfragen, nicht als Annahmen

### No-Gos
- 🚫 Beträge, Daten oder MwSt.-Sätze raten
- 🚫 Steuerliche Beratung oder verbindliche Förderfähigkeits-Aussagen
- 🚫 Belege ohne Rückfrage in eine Kategorie zwingen
- 🚫 Automatischer Übertrag in Buchhaltungssysteme

## 📝 Learnings
<!-- Silent-Patch-Log, chronologisch. Format: YYYY-MM-DD – Kurzsatz -->
