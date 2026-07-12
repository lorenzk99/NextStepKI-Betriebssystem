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
nextstep-os chat              # Interaktiver OS-Agent (REPL mit Gedächtnis)
nextstep-os dashboard         # Web-Dashboard (Skills, Aufgaben, Kontext)
nextstep-os briefing          # ☀️ Tagesbriefing: Aufgaben + Prioritäten
nextstep-os skills list       # Alle Skills anzeigen
nextstep-os pipeline watch    # Pipeline-Watcher starten
nextstep-os review monthly    # Monthly Skill Review
```

---

## CLI-Überblick

```
nextstep-os chat [nachricht]            OS-Agent: REPL (ohne Argument) oder Einzelnachricht
nextstep-os dashboard                   Web-Dashboard: Skills, Aufgaben, Kontext, Feedback
nextstep-os briefing [--llm]            Tagesbriefing (offline; --llm für KI-Summary)
nextstep-os doctor                      Setup-Diagnose (Pfade, API-Key, Register)
nextstep-os stats [skill-id]            Skill-Run-Telemetrie
nextstep-os skills list                 Registrierte Skills auflisten
nextstep-os skills show <id>            Skill-Details anzeigen
nextstep-os skills match <query>        Skill-Matching testen
nextstep-os skills promote <id>         Skill aktivieren (Activation Gate)
nextstep-os tasks list [--alle]         Aufgaben-Übersicht nach Status
nextstep-os tasks show <id>             Aufgaben-Details
nextstep-os context boot                Boot-Kontext anzeigen
nextstep-os context show <skill-id>     Kontext eines Skills anzeigen
nextstep-os pipeline run                Alle Pipeline-Stages EINMAL ausführen
nextstep-os pipeline watch              Status-Watcher (dauerhaft, pollt alle 5s)
nextstep-os pipeline meeting <file>     Meeting-Transkript manuell einspielen
nextstep-os standalone inbox-reply <f>  Inbox Reply Drafter ausführen
nextstep-os standalone lead-dossier <f> Lead-Dossier-Agent ausführen
nextstep-os review monthly              Monthly Skill Review erzeugen
nextstep-os review suggest <skill-id>   LLM-Patch-Vorschlag für einen Skill
nextstep-os feedback record <titel>     Manuellen Feedback-Eintrag anlegen
nextstep-os feedback list               Feedback-Einträge auflisten
```

---

## Wie das System lernt

1. **Silent Patch** (sofort): Feedback im Chat → Skill-MD-Datei bekommt neuen Eintrag in `📝 Learnings` + Regel in SOP
2. **Feedback-DB** (systematisch): Systemische Issues → YAML-Eintrag in `data/feedback/entries/`
3. **Monthly Review** (periodisch): `nextstep-os review monthly` analysiert alle Skills + Feedback + erzeugt Review-Report

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
