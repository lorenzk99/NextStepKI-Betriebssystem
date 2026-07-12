---
id: email-entwurf
name: E-Mail-Entwurf
status: Aktiv
owner: "Lorenz Kopp"
ampel: "🟡"
execution_mode: Strict
nutzungsart: public
keywords:
  - email
  - e-mail
  - mail
  - mail schreiben
  - email schreiben
  - antwort schreiben
  - antwortmail
  - follow up
  - follow-up
  - erstkontakt
  - kundenmail
  - anfrage beantworten
beschreibung: >
  Schreibt einen E-Mail-Entwurf im Kommunikationsstil des Nutzers.
  Deckt Standardsituationen ab: Erstkontakt, Follow-up, Antwort auf
  Kundenanfrage, Partnerkontakt. Der Entwurf muss vor Versand geprüft
  und ggf. angepasst werden.
eingabe:
  - Situation / Anlass (Pflicht) — z.B. "Erstkontakt Physio-Praxis"
  - Empfänger-Info (Pflicht) — Name, Rolle, Praxis/Firma, Kontext
  - Kernbotschaft / Anliegen (Pflicht) — was soll die Mail bewirken?
  - Vorgeschichte (optional) — vorheriger Mailwechsel, Gespräch
  - Konkrete Handlungsaufforderung (optional) — Call, Termin, Angebot
ausgabe:
  - Fertiger E-Mail-Entwurf (Betreff + Body)
  - Kurze Begründung der Struktur (in 1–2 Zeilen)
  - Vorschlag für Follow-up-Zeitpunkt (falls relevant)
context:
  stufe_1_kern:
    - governance/handbuch.md
    - context/personal/kommunikationsstil.md
    - context/personal/firmenprofil.md
    - context/personal/rollenprofil.md
  stufe_2_aufgabe: []
  stufe_3_hintergrund: []
update_quellen:
  - data/feedback/entries/
---

## 🚦 Governance
🟡 GELB – Entwurf wird immer vom Nutzer geprüft und angepasst, bevor er versendet wird. Kein automatischer Versand.

## 📋 Startprotokoll
1. Prüfe, ob Anlass, Empfänger und Kernbotschaft klar sind.
2. Falls Info fehlt: ⏸️ INPUT GATE — konkrete Rückfrage stellen.
3. Lade Kommunikationsstil (Do's, Don'ts, Pet Peeves).
4. Prüfe, ob Empfänger Sie/Du erwartet (Default: Sie bei Erstkontakt B2B).

## 🔧 Arbeitsanweisung (SOP)

### 1. Situation einordnen
Klassifiziere die Mail:
- **Erstkontakt** — kalt oder warm angebahnt?
- **Antwort** — auf welche Anfrage?
- **Follow-up** — nach Meeting, Angebot, Erstkontakt?
- **Partnerkontakt** — Advisor, Jobportal, Verband?

Die Klassifizierung bestimmt Ton und Struktur.

### 2. Kernbotschaft in einem Satz
Formuliere die Kernbotschaft in einem klaren Satz. Alles im Body muss auf diesen Satz einzahlen.

### 3. Struktur wählen
Standard-Struktur für Business-Mails:
1. **Anrede** (Sie/Du nach Regel)
2. **Aufhänger / Bezug** (max. 1 Satz — konkret, nicht floskelhaft)
3. **Kernbotschaft** (was will ich?)
4. **Nutzen für Empfänger** (nur wenn Verkauf/Anfrage)
5. **Handlungsaufforderung** (konkret, mit Optionen wenn Terminanfrage)
6. **Grußformel + Name**

Länge: In der Regel unter 120 Wörter. Kürzer ist besser.

### 4. Entwurf schreiben
Regeln aus Kommunikationsstil beachten:
- Kern zuerst, keine "Ich hoffe..."-Einleitungen
- Keine Marketing-Superlative
- Keine ChatGPT-Floskeln ("Lassen Sie uns...", "Es freut mich sehr...")
- Konkret statt abstrakt (Zahlen, Beispiele, Praxis-Bezug)
- Personalisierung durch Bezug auf Praxis/Branche/letztes Gespräch

**Betreff:**
- Kurz (max. 6–8 Wörter)
- Klar erkennbarer Inhalt, kein Marketing-Sprech
- Bei Antworten: "Re:" beibehalten wenn Original-Thread

### 5. Selbstcheck gegen Pet Peeves
Prüfe Entwurf gegen die Pet-Peeves-Liste im Kommunikationsstil. Streiche alles, was dagegen verstößt.

### 6. Ausgabe
Format:
```
Betreff: [Betreff]

[Body]
```

Dann kurze Meta-Info (1–2 Zeilen):
- Warum diese Struktur gewählt
- Follow-up-Vorschlag falls sinnvoll (z.B. "Nachfassen in 5 Werktagen wenn keine Antwort")

⏸️ **REVIEW GATE:** Der Nutzer prüft und passt an, bevor die Mail rausgeht. Kein automatischer Versand über Gmail-MCP ohne explizite Freigabe.

## ✅ Definition of Done

- ✅ Betreff ist konkret und unter 8 Wörter
- ✅ Body unter 120 Wörter (außer Anlass erfordert mehr)
- ✅ Kernbotschaft steht im ersten oder zweiten Satz
- ✅ Konkrete Handlungsaufforderung am Ende
- ✅ Anrede-Regel (Sie/Du) korrekt angewendet
- ✅ Personalisierung durch mind. 1 konkreten Bezug zum Empfänger
- ✅ Kommunikationsstil vollständig eingehalten (Do's + keine Don'ts + keine Pet Peeves)

### No-Gos
- 🚫 Automatischer Versand ohne Nutzer-Freigabe
- 🚫 Marketing-Superlative ("innovativ", "ganzheitlich", "revolutionär")
- 🚫 ChatGPT-Floskeln ("Lassen Sie uns...", "Es freut mich sehr, Ihnen mitteilen...")
- 🚫 Übertriebene Höflichkeitsformeln vor dem Anliegen
- 🚫 Preise, Zusagen oder Vertragsdetails ohne Absicherung erfinden
- 🚫 Mehr als 1 Ausrufezeichen

## 📝 Learnings
<!-- Silent-Patch-Log, chronologisch. Format: YYYY-MM-DD – Kurzsatz -->
