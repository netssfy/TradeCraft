# Trader Autoresearch Mode

Use this mode when running post-close review and strategy research.
Adopt the same core philosophy as `karpathy/autoresearch`: iterative program-driven improvements under explicit constraints.

## Core Mapping

- Program file: keep a persistent trader instruction file (`trader_program.md`) that defines objective, constraints, and process.
- Mutable artifact: treat strategy code as the primary mutable object (`backend/strategies/<trader_name>_strategy.py`).
- Fixed budget: cap each daily cycle by a small experiment budget (for example 3-5 variants).
- Keep/Discard loop: evaluate each variant and keep only improvements that pass acceptance checks.
- Research logbook: maintain explicit trial history, metrics, and rationale.

## Daily Research Loop (Autoresearch-Aligned)

1. Start from previous accepted strategy baseline.
2. Generate small candidate deltas (parameter tweak, one rule refinement, one risk guard adjustment).
3. Evaluate candidates on fixed datasets/windows with the same metrics.
4. Mark each candidate as `keep` or `discard` with one-line rationale.
5. Promote the best accepted variant as next baseline.
6. Update `trader_program.md` only when process rules need revision, not after every noisy outcome.

## Required Artifacts Per Cycle

- `trader_program.md`: process and objective contract for the trader agent.
- `research_log.md`: dated trials, keep/discard decisions, and reasoning.
- `references/metrics.json` (or tabular equivalent): comparable measurements for baseline and variants.
- Updated strategy Python file implementing `Strategy`.

## Acceptance Gate

Accept a variant only if all conditions hold:
- Interface compatibility remains valid (`initialize` and `on_bar` implemented).
- Risk constraints are not weakened.
- Explainability remains intact (human-readable trigger/exit logic).
- Metrics improve or degrade within predefined tolerance while reducing risk.

## Anti-Patterns

- Do not rewrite strategy wholesale every day.
- Do not change evaluation window between candidate comparisons in the same cycle.
- Do not keep a candidate without explicit evidence in `research_log.md`.
- Do not promote black-box signals without interpretable fallback logic.
