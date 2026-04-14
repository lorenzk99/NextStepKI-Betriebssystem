# Agentic Layer

Das System kennt drei Agent-Klassen. Alle nutzen dasselbe Claude Agent SDK
und greifen auf dieselben Skills, denselben Kontext und dieselbe Governance
zu.

## 1. OS-Agent — interaktiv

**Entry-Point:** `nextstep-os chat "<Anfrage>"` (oder REPL, geplant).

**Zweck:** Generischer, dialogischer Agent. Wählt bei jeder Anfrage den
passenden Skill und führt ihn aus.

**Phasen-Pipeline** (aus `system_prompts/os_agent.md`):

1. **Boot** — persönlichen Kern-Kontext + Governance laden
2. **Skill-Select** — Keyword-Matching, optional Claude-Intent-Matching
3. **Kontext-Load** — Stufe-2 für gewählten Skill
4. **Governance-Check** — Ampel, HIL, Activation-Gate prüfen
5. **Execute** — SDK-Call mit zusammengebautem Systemprompt
6. **Validate** — Output gegen DoD prüfen, HIL-Gates durchsetzen
7. **Feedback** — Silent Patch + Feedback-DB (bei Bedarf)

## 2. Pipeline-Agents — status-getrieben

**Entry-Point:** `nextstep-os pipeline run | watch`.

Fünf spezialisierte Agents, die eine **status-getriebene Pipeline** bilden:

| # | Agent             | Input                          | Output                          |
|---|-------------------|--------------------------------|---------------------------------|
| 1 | meeting_insight   | `data/meetings/inbox/*.md`     | `data/meetings/briefings/*.md`  |
| 2 | task_extractor    | Briefings (Status `Zusammengefasst`) | `data/tasks/*.md` (Neu)    |
| 3 | skill_scout       | Tasks (Status `Neu`)           | Tasks (Status `Skill zugewiesen`) |
| 4 | skill_executor    | Tasks (Status `Skill zugewiesen`) | Tasks (Status `Skill ausgeführt` / `Wartet auf Review`) |
| 5 | feedback_logger   | Tasks (Status `Skill ausgeführt`) | Tasks (Status `Erledigt`) + `data/feedback/entries/*.yaml` |

Der **Runner** (`src/nextstep_os/agents/runner.py`) polled das `data/`-Verzeichnis
und triggert die jeweils nächste Stage. `pipeline watch` startet den Runner
in einer Endlosschleife.

### Beispielhafter Zyklus

```
1. Meeting-Transkript droppen in data/meetings/inbox/
2. Runner → Meeting-Insight erstellt Briefing
3. Runner → Task-Extractor legt N Tasks an
4. Runner → Skill-Scout ordnet jedem Task einen Skill zu
5. Runner → Skill-Executor führt SOP aus (stoppt an HIL-Gates)
6. Mensch reviewt (bei 🟡) / greift ein (bei ⏸️)
7. Runner → Feedback-Logger schließt den Task ab
```

## 3. Standalone-Agents — single-shot

**Entry-Point:** `nextstep-os standalone <name> <file>`.

Kurze, gezielte Agenten für konkrete Use-Cases. Keine Pipeline-Integration.

| Agent                | Zweck                                                   |
|----------------------|---------------------------------------------------------|
| inbox_reply_drafter  | E-Mail-Antwort-Entwurf gemäß Kommunikationsstil         |
| lead_dossier         | Lead-Infos extrahieren + Unternehmens-/Ansprechpartner-Profil |

Beide Agents laden den persönlichen Boot-Kontext (Firmenprofil, Rollenprofil,
Kommunikationsstil) für eine stilistische Verankerung.

## DryRun-Modus

Wenn `ANTHROPIC_API_KEY` fehlt oder das SDK nicht installiert ist, laufen
alle Agents im **DryRun-Modus**: sie bauen den Systemprompt vollständig auf,
führen aber keinen SDK-Request aus. Stattdessen wird der Prompt (gekürzt)
ausgegeben. Das macht die Pipeline offline inspizierbar und eignet sich für:

- Entwicklungs-Tests ohne Kosten
- CI / GitHub Actions
- Prompt-Debugging
- Onboarding (»Was würde der Agent tun?«)

## Modell-Zuordnung

| Agent-Klasse    | Default-Modell        | Begründung                    |
|-----------------|-----------------------|--------------------------------|
| OS-Agent        | claude-opus-4-6       | Beste Qualität, dialog-lastig |
| Pipeline        | claude-sonnet-4-6     | Schnell, kostengünstig        |
| Fast-Variante   | claude-haiku-4-5      | Trigger / Status-Updates      |

Überschreibbar über `.env`:

```ini
NEXTSTEP_MODEL_OS_AGENT=claude-opus-4-6
NEXTSTEP_MODEL_PIPELINE=claude-sonnet-4-6
NEXTSTEP_MODEL_FAST=claude-haiku-4-5-20251001
```
