# NextStepKI – KI-Betriebssystem

Ein selbstverbesserndes KI-Betriebssystem, das Fähigkeiten (Skills), Kontext und Governance so organisiert, dass Arbeit skalierbar, wiederholbar und qualitätsgesichert wird. Kein Use-Case-Silo, sondern ein vernetztes System, in dem die Intelligenz nicht im einzelnen Agenten liegt, sondern im System selbst.

> **Kernprinzip:** Agenten sind austauschbare Ausführungseinheiten. Die Intelligenz liegt in Skills, Kontext, Governance und der integrierten Lernschleife.

---

## Was drin ist

| Baustein | Ort | Zweck |
|---|---|---|
| **OS-Agent** | `src/nextstep_os/agents/os_agent.py` | Interaktiver General-Purpose-Agent, Skill-Selection via Semantic Matching |
| **Pipeline-Agents** | `src/nextstep_os/agents/pipeline/` | 5-Agent-Kette: Meeting → Task → Skill-Scout → Executor → Feedback |
| **Standalone-Agents** | `src/nextstep_os/agents/standalone/` | Inbox Reply Drafter, Lead Dossier |
| **Skill-Datenbank** | `data/skills/` | Markdown-Dateien mit Frontmatter (je Skill eine Datei) |
| **Kontext-Datenbank** | `data/context/` | Persönliches Profil + geteilte Wissensquellen |
| **Governance-Handbuch** | `data/governance/handbuch.md` | Ampel-System, HIL, Execution-Modi, Activation Gate |
| **Feedback-DB** | `data/feedback/` | Strukturierte Lernschleife |
| **System-Prompts** | `system_prompts/` | Alle Agent-Systemprompts als Markdown |

---

## Setup in 5 Schritten

```bash
# 1. Abhängigkeiten installieren
pip install -e ".[dev]"

# 2. Environment konfigurieren
cp .env.example .env
# → .env bearbeiten: ANTHROPIC_API_KEY eintragen

# 3. Kontextprofil befüllen
# → data/context/personal/*.md durchgehen und Platzhalter ersetzen
#    Alternative: docs/context-profil-interview.md als Interview-Prompt nutzen

# 4. Governance-Handbuch anpassen
# → data/governance/handbuch.md: Owner-Rollen, Datenklassen, Kennzeichnungspflichten

# 5. Starten
nextstep-os chat              # Interaktiver OS-Agent
nextstep-os dashboard         # Web-Dashboard (Skills ansehen & anlegen)
nextstep-os skills list       # Alle Skills anzeigen
nextstep-os pipeline run      # Pipeline-Watcher starten
nextstep-os review            # Monthly Skill Review
```

---

## CLI-Überblick

```
nextstep-os chat                        Interaktive Session mit dem OS-Agent
nextstep-os dashboard                   Web-Dashboard: Skills, Kontext, Feedback, Telemetrie
nextstep-os skills list                 Registrierte Skills auflisten
nextstep-os skills show <id>            Skill-Details anzeigen
nextstep-os context list                Kontext-Einträge auflisten
nextstep-os pipeline run                Status-Watcher für Pipeline-Agents starten
nextstep-os pipeline meeting <file>     Meeting-Transkript manuell einspielen
nextstep-os standalone inbox            Inbox Reply Drafter ausführen
nextstep-os standalone lead <file>      Lead-Dossier-Agent ausführen
nextstep-os review                      Monthly Skill Review starten
nextstep-os feedback log                Manuellen Feedback-Eintrag anlegen
```

---

## Wie das System lernt

1. **Silent Patch** (sofort): Feedback im Chat → Skill-MD-Datei bekommt neuen Eintrag in `📝 Learnings` + Regel in SOP
2. **Feedback-DB** (systematisch): Systemische Issues → YAML-Eintrag in `data/feedback/entries/`
3. **Monthly Review** (periodisch): `nextstep-os review` analysiert alle Skills + Feedback + erzeugt Review-Report

---

## Architektur auf einen Blick

```
                    ┌──────────────────────┐
                    │   OS-Agent (CLI)     │ ← du sprichst hier mit dem System
                    └──────────┬───────────┘
                               │
     ┌─────────────────────────┼─────────────────────────┐
     │                         │                         │
     ▼                         ▼                         ▼
┌─────────┐              ┌──────────┐             ┌────────────┐
│ Skills  │              │ Kontext  │             │ Governance │
│   DB    │              │    DB    │             │  Handbuch  │
└─────────┘              └──────────┘             └────────────┘
     ▲                         ▲                         ▲
     │                         │                         │
     └──────┬──────────────────┴─────────────────────────┘
            │
   ┌────────┴────────┐
   │   Agentic Layer  │
   ├─────────────────┤
   │ Pipeline:       │
   │   Meeting →     │
   │   Task →        │
   │   Scout →       │
   │   Executor →    │
   │   Feedback      │
   ├─────────────────┤
   │ Standalone:     │
   │   Inbox Reply   │
   │   Lead Dossier  │
   └─────────────────┘
```

Tiefergehende Erklärungen:
- `docs/architektur.md` – Designprinzipien & Systemaufbau
- `docs/skill-playbook.md` – Wie neue Skills gebaut werden
- `docs/agentic-layer.md` – Die 3 Agenten-Typen
- `docs/context-profil-interview.md` – Interview-Prompt zum Kontextprofil-Erstellen

---

## Lizenz

Proprietär – NextStepKI.
