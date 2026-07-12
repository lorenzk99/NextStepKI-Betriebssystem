# Quickstart

Fünf Schritte, um dein eigenes KI-Betriebssystem in Betrieb zu nehmen.

## 1. Installation

```bash
git clone <repo-url>
cd NextStepKI-Betriebssystem
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## 2. Environment einrichten

```bash
cp .env.example .env
# Trage deinen ANTHROPIC_API_KEY ein und passe ggf. die Modell-IDs an.
```

Ohne API-Key läuft das System im **DryRun-Modus**: alle Phasen bis zum
Modell-Call werden ausgeführt, der eigentliche SDK-Request entfällt. Ideal
zum Testen der Pipeline, ohne Kosten zu verursachen.

## 3. Setup prüfen

```bash
nextstep-os doctor
```

Prüft API-Key, Skill-Register, Kontext-Register, Governance-Handbuch und
SDK-Verfügbarkeit.

## 4. Persönlichen Kontext befüllen

Die Dateien unter `data/context/personal/` sind **Templates mit Platzhaltern**.
Befülle sie mit deinen echten Infos (Firma, Rolle, Team, Ziele,
Kommunikationsstil). Der OS-Agent lädt diese Dateien bei jedem Boot.

Optional: Nutze den Interview-Prompt aus `docs/context-profil-interview.md`,
um den Kontext durch Selbst-Interview aufzubauen.

## 5. OS-Agent verwenden

```bash
# Einzelne Anfrage (DryRun oder echter Call je nach API-Key)
nextstep-os chat "Erstelle ein Angebot für den Testkunden"

# Skills & Kontext inspizieren
nextstep-os skills list
nextstep-os skills show angebot-erstellen
nextstep-os skills match "Angebot schreiben"
nextstep-os context boot
nextstep-os context show angebot-erstellen

# Pipeline (einmal durchlaufen lassen)
nextstep-os pipeline run

# Pipeline (Watcher-Modus)
nextstep-os pipeline watch --interval 10

# Feedback
nextstep-os feedback record "Idee XYZ" --typ verbesserungs-idee
nextstep-os feedback list
nextstep-os feedback review

# Standalone-Agenten
nextstep-os standalone inbox-reply path/to/mail.txt
nextstep-os standalone lead-dossier path/to/lead.txt --projekt "ACME: Pilot"
```

## 6. Neuen Skill anlegen

Zwei Wege:

**(a) Konversationell** — über den OS-Agent:

```bash
nextstep-os chat "Erstelle einen neuen Skill für Rechnungen schreiben"
```

Der Meta-Skill `neuen-skill-erstellen` führt dich strukturiert durch das
Interview.

**(b) Manuell:**

1. Lege eine neue Datei unter `data/skills/<slug>.md` an
2. Orientiere dich am Frontmatter-Schema der existierenden Skills
3. Trage den Skill in `data/skills/_index.yaml` ein
4. Starte mit Status `Entwurf`, führe 3+ Testläufe, dann auf `Aktiv` setzen

## 7. Pipeline-Zyklus im Überblick

```
data/meetings/inbox/*.md     → Meeting-Insight-Agent
data/meetings/briefings/*.md → Task-Extractor-Agent
data/tasks/*.md (Neu)         → Skill-Scout-Agent
data/tasks/*.md (Skill zugewiesen)  → Skill-Executor-Agent
data/tasks/*.md (Skill ausgeführt)  → Feedback-Logger-Agent
```

Jeder Agent aktualisiert das `status`-Feld im Frontmatter. Der
`runner` triggert die nächste Stage, sobald der Status passt.
