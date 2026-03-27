# Trader Skill / Prompt Template

Use this template when exporting a trained trader so another AI agent can execute it.
Trainer phase output should only create trader artifacts.
Do not implement strategy code during trainer generation.
The trader artifact must instruct the executing agent to output strategy code compatible with `backend/app/trading/strategy.py`.

## Trader Naming and Location (Required)

- Save each trader under: `backend/data/traders/{id}`
- `{id}` must be trait-based and short:
  - Include key style signals (for example: trend, meanrev, event)
  - Include risk flavor (for example: cons, bal, aggr)
  - Keep length at 8-24 chars, lowercase letters, digits, and hyphens only
- Example names:
  - `trend-bal-swing`
  - `meanrev-cons-a50`
  - `event-aggr-earn`

## Option A: Trader Skill Folder

Recommended structure:

```text
backend/data/traders/{id}/
  SKILL.md
  references/
    metrics.json
    trader_program.md
    risk_policy.md
    research_log.md
```

`SKILL.md` should direct the agent to:
- Read style card and risk policy first.
- Run the daily autoresearch loop.
- Output or update one strategy file:
  - `backend/strategies/{id}_strategy.py`
- Ensure the class inherits `Strategy` and implements required methods.
- Do not pre-commit concrete algorithm rules during trainer generation.

## Option B: Standalone Trader Prompt

If no folder is needed, still create `backend/data/traders/{id}/` and place one `trader_program.md` with:
- Objective and scope.
- Allowed instruments and risk bounds.
- Daily keep/discard experiment loop.
- Output contract: write final strategy code implementing `Strategy`.

## Minimal Output Contract (Must Include)

```text
1) Trader ID and Folder Path (`backend/data/traders/{id}`)
2) Trader execution target strategy path convention (`backend/strategies/{id}_strategy.py`)
3) Strategy class/interface requirements for execution phase
4) Strategy-authoring protocol (how trader should design rules when executed)
5) Risk policy constraints and forbidden actions
6) Latest Keep/Discard Decision Summary
```

## Required Final Line For Backend Parsing

Always end the trainer run with exactly one line:

```text
FINAL_TRAITS_JSON: {"risk_appetite":"...","holding_horizon":"...","signal_preference":"...","position_construction":"...","exit_discipline":"...","universe_focus":"..."}
```

Rules:
- Use valid JSON object syntax.
- Keep it on a single line.
- Do not append extra text to that line.

## Execution Note for AI Agents

When executing the trader skill/prompt:
- Use latest approved baseline strategy as starting point.
- Modify only what is needed for the current cycle.
- Produce deterministic, inspectable rules.
- Return updated strategy code as the primary deliverable.
