# Daily Post-Close Loop

Run this loop after each market close.
Goal: update trader understanding and strategy parameters with traceable evidence.

## Step 1: Market Replay

- Summarize index and sector behavior for the session.
- Record watchlist performance and notable outliers.
- Mark whether current strategy regime assumptions still hold.

## Step 2: Trade Review

- For each executed or hypothetical trade, record:
  - Signal trigger
  - Entry/exit timing
  - Position size
  - P/L and risk-adjusted quality
- Identify errors: late entry, oversized position, rule violation, overtrading.

## Step 3: New Information Research

- Collect high-impact updates:
  - Earnings and guidance
  - Policy or macro events
  - Sector rotation and liquidity shifts
- Separate facts from assumptions.

## Step 4: Strategy Update

- Decide whether to:
  - Keep parameters unchanged
  - Tune thresholds/sizing
  - Disable a regime-sensitive rule
  - Add a new rule only if it remains explainable
- Keep one update cycle focused; avoid overfitting to one day.
- Compare candidates under the same evaluation window and mark each as `keep` or `discard`.

## Step 5: Change Log and Next-Day Plan

- Log each change as:
  - What changed
  - Why it changed
  - Expected effect
  - Invalidating condition
- Publish next-day watch points and risk limits.

## Daily Output Template

```text
Date:
Market Summary:
Trader Style Card:
Trades Reviewed:
Research Highlights:
Candidate Variants (keep/discard + reason):
Strategy Changes:
Risk Status:
Next-Day Watch Points:
```

## Hard Constraints

- No post-close output should imply guaranteed profitability.
- Any strategy update must preserve compatibility with the required `Strategy` interface.
- Any strategy update must keep risk controls explicit and inspectable.
