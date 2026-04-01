---
name: auto-quant-trainer
description: Run an autoresearch-style strategy R&D loop for TradeCraft. Use when an agent must research a target instrument, inspect local market data through backend CLI commands, run backtests through backend CLI, and iteratively improve a Strategy-compatible Python implementation under backend/data/traders/{trader_id}/strategy while enforcing immutable objective metrics and a hard max of 10 iterations.
---

# Auto Quant Trainer

Execute the workflow in [program.md](program.md) as the source of truth.

## Workflow

1. Resolve runtime context first:
- Identify `TRADER_ID`.
- Read objective metrics from `backend/data/traders/{TRADER_ID}/references/metrics.json`.
- Treat objective metrics as immutable.

2. Use backend CLI for data and backtests:
- Run from `backend/`.
- Data access:
  - `python -m app.cli data availability`
  - `python -m app.cli data slice --market CN --symbol 600519 --interval 1d --start 2024-01-01 --end 2025-12-31`
  - `python -m app.cli data file --market CN --symbol 600519 --interval 1d --period 2025-03 --limit 30`
- Backtest:
  - `python -m app.cli backtest run --trader-id {TRADER_ID} --start-date 2025-01-01 --end-date 2026-03-31`
  - `python -m app.cli backtest report --trader-id {TRADER_ID} --run-id {RUN_ID}`

3. Implement strategy under strict interface rules:
- Write strategy files only under `backend/data/traders/{TRADER_ID}/strategy`.
- Ensure final strategy subclasses `Strategy` from `backend/app/trading/strategy.py`.
- Implement `initialize` and `on_bar` at minimum.

4. Research and iterate:
- Permit web research for target instrument and regime context.
- Permit temporary local Python scripts for one-off analysis.
- Evaluate against immutable objective metrics after each backtest.
- Stop when objectives are met or when `MAX_ITERATIONS=10` is reached.

## Guardrails

- Never edit objective thresholds in `metrics.json`.
- Never bypass CLI for the required data-access/backtest loop.
- Never output a strategy that does not inherit `Strategy`.
- Keep each iteration auditable: hypothesis, change, result, decision.
