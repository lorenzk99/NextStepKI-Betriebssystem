# Kontextprofil-Interview

Mit diesem Interview-Prompt befüllst du deinen persönlichen Kern-Kontext
(Stufe 1) in **45–60 Minuten**. Ergebnis: fünf ausgefüllte Dateien unter
`data/context/personal/`.

## So läuft's

1. Öffne einen frischen Claude-Chat (oder nutze `nextstep-os chat`).
2. Kopiere den Prompt unten in die erste Nachricht.
3. Beantworte jede Frage aus deiner Sicht — ruhig lang, ruhig unperfekt.
4. Am Ende produziert Claude **fünf Markdown-Blöcke**, die direkt in die
   Templates passen.

## Der Interview-Prompt

```
Du bist mein Onboarding-Assistent. Wir bauen gemeinsam mein persönliches
Kontextprofil für ein KI-Betriebssystem auf.

Ziel: Am Ende fünf fertige Markdown-Dateien:
  1. firmenprofil.md
  2. rollenprofil.md
  3. kommunikationsstil.md
  4. team-kontext.md
  5. prioritaeten-und-ziele.md

Stelle mir Fragen — eine nach der anderen. Nach jeder Antwort fasst du
kurz zusammen, was du mitnimmst, und stellst die nächste Frage.

Folge dieser Struktur:

--- FIRMENPROFIL ---
- Firmenname, Gründungsjahr, Rechtsform
- Branche, Hauptprodukt/Hauptdienstleistung
- Zielgruppe & typische Kunden
- Alleinstellungsmerkmal / Positionierung
- Werte / Prinzipien
- Größe (Umsatz, MA)

--- ROLLENPROFIL ---
- Deine Rolle / Titel
- Kernverantwortungen (max. 5)
- Entscheidungsbefugnisse
- Tools, die du täglich nutzt
- Typische Wochen-Rhythmen
- Herausforderungen / Energiefresser
- Stärken / worin du brillierst

--- KOMMUNIKATIONSSTIL ---
- Ansprache: Du/Sie
- Ton: sachlich / warm / direkt / ...
- Emoji-Nutzung
- Lieblings-Formulierungen
- No-Gos (Wörter, Phrasen)
- Signatur / Grußformel

--- TEAM-KONTEXT ---
- Direkte Team-Mitglieder (Name, Rolle, Superpower)
- Key-Stakeholder außerhalb (Investoren, Kunden, Partner)
- Kommunikationskanäle (Slack, E-Mail, Teams)
- Meeting-Rhythmen

--- PRIORITÄTEN & ZIELE ---
- #1-Priorität dieses Quartal
- Top-3-Fokusthemen
- Offene große Entscheidungen
- Deadlines der nächsten 30 Tage
- Jahresziele / OKRs

Wenn alle Themen durch sind, lieferst du fünf saubere Markdown-Dokumente
im Format der jeweiligen Templates unter `data/context/personal/`.
Behalte Platzhalter nicht bei — ersetze sie durch meine Antworten.
```

## Was danach passiert

1. Übertrage die fünf Outputs in die jeweiligen Dateien unter
   `data/context/personal/`.
2. Prüfe: `nextstep-os context boot` zeigt die Stufe-1-Profile (Firmen-, Rollenprofil, Kommunikationsstil + Governance); Stufe-2-Profile (Team, Prioritäten) erscheinen im Skill-Kontext.
3. Teste: `nextstep-os chat "Was ist heute mein Fokus?"` — der Agent
   sollte aus deinem Kontext zitieren.

## Update-Rhythmus

| Datei                      | Update-Rhythmus       |
|----------------------------|-----------------------|
| firmenprofil.md            | quartalsweise         |
| rollenprofil.md            | quartalsweise         |
| kommunikationsstil.md      | bei Bedarf            |
| team-kontext.md            | bei Team-Änderung     |
| prioritaeten-und-ziele.md  | monatlich             |

Trage den Rhythmus auch in `data/context/_index.yaml` (`aktualisierung`)
ein, damit Monthly Reviews die Quellen anzeigen.
