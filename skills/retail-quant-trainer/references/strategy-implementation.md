# Strategy Implementation Contract

All trained traders must implement strategies compatible with:
`backend/app/trading/strategy.py`

## Required Interface

- Class must inherit from `Strategy`.
- Must implement:
  - `initialize(self, context) -> None`
  - `on_bar(self, context, bar) -> None`

## Context Capabilities

- Read portfolio state via `context.portfolio.cash` and `context.portfolio.positions`.
- Read historical bars via `context.history(...)` with no look-ahead bias.
- Place orders via `context.order(symbol, qty, ...)`.

## Trainer-Phase Boundary

- In trainer generation phase, define only implementation contract and guardrails.
- Do not provide concrete indicator choices, fixed thresholds, or explicit trading formulas.
- Leave strategy rule design to the trader execution phase.

## Contract Requirements to Embed in Trader Artifact

- Strategy class must inherit `Strategy`.
- `initialize` and `on_bar` methods are mandatory.
- Use only available context APIs for portfolio, history, and order placement.
- Keep all future strategy logic explainable and auditable.
- Preserve risk-policy constraints defined by trader references.

## Pre-Delivery Review

- Interface compliance checked.
- Strategy-authoring protocol documented in plain language.
- Position and loss policy limits documented in plain language.
- Any future parameter updates tied to evidence from recent review cycle.
