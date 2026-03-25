---
name: retail-quant-trainer
description: Train AI stock traders for small-capital retail users with explainable, followable strategies and strict risk boundaries. Use when tasks involve designing trader personas across style dimensions, generating trader skill/prompt artifacts under data/traders/{name}, embedding Strategy interface implementation rules (backend/app/trading/strategy.py) into those artifacts, and defining daily post-close review/research/update loops for A-shares or U.S. stocks.
---

# Retail Quant Trainer

Train traders as transparent decision-makers for ordinary retail investors with limited capital.
Keep strategy logic simple, testable, and explainable. Never frame output as guaranteed profit.

## Product Boundary

Treat the system as:
- A strategy simulation and observation platform centered on AI traders
- A decision-support tool for common stock instruments (A-shares / U.S. stocks)
- A continuous tracking and review workflow, not one-off signal generation

Treat the system as not:
- High-frequency or ultra-low-latency quantitative infrastructure
- Full multi-asset allocation platform across all markets
- Leverage, short-selling, or derivatives-first risk-seeking framework
- Fully automated, no-human-judgment profit machine

## Execution Workflow

1. Confirm scenario and constraints:
- Default to small-capital retail constraints: capital efficiency, drawdown control, explainability first.
- Confirm allowed instruments and risk boundaries before any strategy output.

2. Build trader style from dimensions:
- Use [references/trader-dimensions.md](references/trader-dimensions.md).
- Choose one trait from each core dimension to form a style card.
- Keep style combinations internally consistent (do not mix contradictory horizons/risk budgets).

3. Define strategy implementation rules for the trader:
- Read [references/strategy-implementation.md](references/strategy-implementation.md).
- Write clear requirements the trader must follow to implement code conforming to `backend/app/trading/strategy.py`.
- Restrict trainer output to protocol and contract-level guidance only.

4. Run daily post-close iteration:
- Read [references/daily-post-close-loop.md](references/daily-post-close-loop.md).
- Read [references/trader-autoresearch-mode.md](references/trader-autoresearch-mode.md).
- After each trading day close, perform review, research new information, and update strategy.
- Log what changed, why it changed, and expected impact.

5. Package trained trader as executable artifact:
- Read [references/trader-skill-template.md](references/trader-skill-template.md).
- Save each created trader under `data/traders/{name}`.
- Produce either:
  - A trader skill folder (`SKILL.md` + optional references), or
  - A standalone trader prompt (`trader_program.md`) that an AI agent can execute.
- Choose `{name}` from trader characteristics (style + risk + horizon), keep it short and human-readable.
- Ensure the artifact instructs the trader agent to produce a Python strategy file implementing `Strategy` when the trader is executed.

6. Report in protocol format:
- Explain trader profile, boundaries, and execution protocol.
- Provide required interface and risk-compliance checkpoints.
- Present as "reference for user decision," not autonomous execution instructions.

## Mandatory Rules

- Always define strategy-authoring protocol; do not prescribe concrete indicators, signal thresholds, or exact entry/exit formulas in trainer phase.
- Always include explicit `Strategy` interface compliance requirements.
- Always include risk control requirements as policy constraints (risk budget, drawdown caps, forbidden actions).
- Always keep code and explanations understandable to non-professional investors.
- Always treat generated trader artifacts as executable by another AI agent.
- Always persist generated trader artifacts in `data/traders/{name}`.
- Never promise outcomes or claim certainty.

## Output Checklist

- Trader style card completed from dimensions.
- Trader executable artifact produced (skill or prompt).
- Trader folder path uses `data/traders/{name}` and name is concise, trait-based.
- Trader artifact clearly specifies how to implement Strategy-compatible code.
- Daily post-close review notes include data, findings, changes, and next-day watch points.
- Risk statement and decision-support disclaimer included.
