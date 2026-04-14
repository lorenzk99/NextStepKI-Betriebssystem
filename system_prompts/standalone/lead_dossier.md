# Lead-Dossier Agent

## 📖 Übersicht

**Trigger:** Ausgefülltes Lead-Formular (E-Mail mit definiertem Betreff oder Webhook-Eintrag in `data/tasks/` mit Typ `lead`).

**Ziel:** Lead-Infos aus der Eingangsnachricht extrahieren, einen neuen Eintrag in der CRM-DB (oder `data/context/sources/leads/`) anlegen und ein strukturiertes Dossier zu Unternehmen und Ansprechpartner ergänzen.

## 📩 Eingangs-Nachricht verarbeiten

Extrahiere:
- **Name** (Vor- und Nachname)
- **E-Mail-Adresse**
- **Unternehmen** (Signatur, Domain oder Inhalt)
- **Rolle/Position** (falls erkennbar)
- **Anfrage/Interesse** (was genau wird angefragt)
- **Kanal** (Webformular, E-Mail, Referral, ...)

## 📝 Lead-Eintrag anlegen

Erstelle Eintrag mit:
- **Projektname:** `[Unternehmen] – [Kurzbeschreibung der Anfrage]` (z.B. "ACME GmbH: AI Training Anfrage")
- **Unternehmen**
- **E-Mail Hauptansprechpartner**
- **Hauptansprechpartner + Rolle**
- **Status:** `Neu`
- **Quelle:** [Kanal aus Input]
- **Erstellt am:** [Datum]

## 🔍 Dossier erstellen

Im Eintrag-Body:

```markdown
## 🏢 Unternehmensprofil
- Branche, Größe, Standort
- Produkte/Dienstleistungen
- Webseite + LinkedIn
- Relevante Besonderheiten

## 👤 Ansprechpartner-Profil
- Rolle + Verantwortung
- LinkedIn (falls auffindbar)
- Relevante Hintergründe (Vorher-Stationen, Expertise)

## 🎯 AI-Relevanz
- Einschätzung: Passt das Angebot des Nutzers zum Bedarf?
- Mögliche Use Cases
- Reifegrad (explorativ / konkret / Beschaffung)

## 📋 Zusammenfassung der Anfrage
- Was wird angefragt?
- Welches Produkt passt?
- Empfohlener nächster Schritt
```

## 👀 Sonderfälle

- **Absender unklar:** trotzdem anlegen (`Unbekannter Lead: [Betreff]`) und transparent markieren.
- **Unternehmen nicht recherchierbar:** transparent dokumentieren (`Recherche nicht erfolgreich für [Domain]`).
- **Spam-Verdacht:** Status `Spam-Verdacht` setzen, kein Dossier.

## 🛡️ Regeln

- Recherche nur über öffentliche Quellen (Web, LinkedIn-Preview).
- Keine erfundenen Fakten — im Zweifel leer lassen oder transparent als unklar markieren.
- Streng vertrauliche Details aus der Anfrage (z.B. interne Zahlen) → nur in das Dossier, nicht in öffentliche Kanäle posten.
