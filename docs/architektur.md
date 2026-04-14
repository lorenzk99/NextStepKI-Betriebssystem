# Architektur

## Leitprinzip

**Intelligenz im System, nicht im Agenten.** Die Agents (OS + Pipeline +
Standalone) sind generisch. Die spezifische Intelligenz steckt in:

- **Skills** — Markdown-Dateien mit Frontmatter unter `data/skills/`
- **Kontext** — Persönliches Profil + geteilte Quellen unter `data/context/`
- **Governance** — Regeln unter `data/governance/handbuch.md`
- **Feedback** — Selbst-Optimierung unter `data/feedback/`

Ein neuer Use-Case = eine neue Markdown-Datei. Keine Code-Änderung.

## Storage-Modell

Dateibasiert. Markdown mit YAML-Frontmatter + `_index.yaml`-Schnellregister.

Vorteile:
- Git-versionierbar (Diff, Blame, Reviews)
- Plattform-agnostisch
- Von Menschen lesbar und editierbar
- Keine externe DB nötig

## Komponenten

```
┌──────────────────────────────────────────────────────────────┐
│                         OS-Agent (CLI)                       │
│  Phasen: Boot → Skill-Select → Kontext → Governance →        │
│           Execute → Validate → Feedback                      │
└──────────────────────────────────────────────────────────────┘
              │                    │                  │
              ▼                    ▼                  ▼
     ┌────────────────┐   ┌────────────────┐  ┌────────────────┐
     │ skill_loader   │   │ context_loader │  │  governance    │
     │ (Matching)     │   │ (3-Stufen)     │  │ (Ampel/HIL)    │
     └────────────────┘   └────────────────┘  └────────────────┘
              │                    │                  │
              └──────┬─────────────┴─────────┬────────┘
                     ▼                       ▼
            ┌────────────────┐      ┌────────────────┐
            │  prompt_builder│      │   sdk_bridge   │
            │ (Systemprompt) │ ───▶ │  (Claude SDK)  │
            └────────────────┘      └────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Pipeline (status-getrieben)               │
│                                                              │
│  inbox/*.md → Meeting-Insight → briefings/*.md               │
│             → Task-Extractor → tasks/*.md (Neu)              │
│             → Skill-Scout    → tasks/*.md (Zugewiesen)       │
│             → Skill-Executor → tasks/*.md (Ausgeführt)       │
│             → Feedback-Log   → tasks/*.md (Erledigt)         │
│                              + data/feedback/entries/*.yaml  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                      Standalone-Agenten                      │
│   inbox_reply_drafter · lead_dossier                         │
└──────────────────────────────────────────────────────────────┘
```

## 3-Stufen-Kontext-Hierarchie

| Stufe | Zweck                          | Wann geladen                  |
| ----- | ------------------------------ | ----------------------------- |
| 1     | Kern (Identität, Governance)   | Immer (Boot)                  |
| 2     | Aufgaben-Kontext (Skill)       | Bei aktivem Skill             |
| 3     | Hintergrund / Archiv           | On-Demand (`--mit-hintergrund`) |

Token-Budgets sind in `config.py` / `.env` konfigurierbar.

## Governance-Engine

- **Ampel:** 🟢 autonom · 🟡 Review-Gate · 🔴 nur Mensch
- **HIL-Marker** (⏸️): approval / input / review im SOP-Body
- **Execution-Mode:** Strict (kein Web) vs. Search (mit Guard Rails)
- **Activation Gate:** Skills im Status `Entwurf` brauchen 3+ Testläufe

Jeder Skill-Run liefert eine `GovernanceDecision`, die vom OS-Agent und
Executor bindend respektiert wird.

## Feedback-Loop

Zwei Wirkmechanismen:

1. **Silent Patch:** Änderungen direkt in der Skill-MD (`## 📝 Learnings`).
2. **Feedback-DB:** YAML-Einträge in `data/feedback/entries/` für Monthly
   Reviews.

## Erweiterungspunkte

- **MCP-Server:** In `.env.example` dokumentiert. Mail/Calendar/CRM-Zugriff
  bindet der OS-Agent zur Laufzeit ein, sobald die MCP-URLs gesetzt sind.
- **Neue Agents:** Systemprompt in `system_prompts/` + Python-Modul in
  `src/nextstep_os/agents/` + CLI-Binding in `cli.py`.
- **Neue Kontext-Typen:** `ContextTyp`-Enum erweitern + Loader-Zweig in
  `context_loader._load_entry`.
