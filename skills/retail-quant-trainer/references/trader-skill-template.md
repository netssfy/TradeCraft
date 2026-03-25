# Trader Skill / Prompt Template

Use this template when exporting a trained trader so another AI agent can execute it.
Trainer phase output should only create trader artifacts.
Do not implement strategy code during trainer generation.
The trader artifact must instruct the executing agent to output strategy code compatible with `backend/app/trading/strategy.py`.

## Trader Naming and Location (Required)

- Save each trader to: `data/traders/{name}`
- `{name}` must be trait-based and short:
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
data/traders/{name}/
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
  - `backend/strategies/{name}_strategy.py`
- Ensure the class inherits `Strategy` and implements required methods.
- Do not pre-commit concrete algorithm rules during trainer generation.

## Option B: Standalone Trader Prompt

If no folder is needed, still create `data/traders/{name}/` and place one `trader_program.md` with:
- Objective and scope.
- Allowed instruments and risk bounds.
- Daily keep/discard experiment loop.
- Output contract: write final strategy code implementing `Strategy`.

## Minimal Output Contract (Must Include)

```text
1) Trader Name and Folder Path (`data/traders/{name}`)
2) Trader execution target strategy path convention (`backend/strategies/{name}_strategy.py`)
3) Strategy class/interface requirements for execution phase
4) Strategy-authoring protocol (how trader should design rules when executed)
5) Risk policy constraints and forbidden actions
6) Latest Keep/Discard Decision Summary
```

## Execution Note for AI Agents

When executing the trader skill/prompt:
- Use latest approved baseline strategy as starting point.
- Modify only what is needed for the current cycle.
- Produce deterministic, inspectable rules.
- Return updated strategy code as the primary deliverable.
