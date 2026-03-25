# Trader Dimensions

Use these dimensions to build diverse trader styles for training.
Pick one trait per dimension unless the task explicitly asks for a hybrid.

## 1) Risk Appetite

- Conservative: prioritize capital preservation, tight drawdown threshold.
- Balanced: accept moderate volatility for stable growth.
- Aggressive within bounds: pursue higher upside but still keep hard risk caps.

## 2) Holding Horizon

- Short swing: hold for days to 2 weeks.
- Medium trend: hold for 2 to 8 weeks.
- Event-driven tactical: hold around specific earnings/news windows with strict exit timing.

## 3) Signal Preference

- Trend-following: breakout, moving-average alignment, momentum continuation.
- Mean-reversion: oversold bounce, deviation return to baseline.
- Event-confirmed: combine technical trigger with explicit news/fundamental catalyst.

## 4) Position Construction

- Single-entry fixed size: easy to track for beginners.
- Layered entry: split into 2-3 tranches with predefined add/reduce rules.
- Risk-budget sizing: size by stop distance and max loss per trade.

## 5) Exit Discipline

- Fixed stop + fixed take-profit.
- Trailing stop after profit threshold.
- Time stop + condition stop (close after N bars/days if thesis not realized).

## 6) Universe Focus

- Large/mega-cap leaders only.
- Sector leaders with liquidity filter.
- Narrow watchlist (5-20 symbols) with deep follow-up.

## Style Card Template

Fill this card before coding a strategy:

```text
Trader Name:
Risk Appetite:
Holding Horizon:
Signal Preference:
Position Construction:
Exit Discipline:
Universe Focus:
Max Risk per Trade:
Max Portfolio Drawdown:
```

## Consistency Rules

- Match holding horizon with signal type (for example, avoid using minute-level noise for medium trend).
- Keep position sizing method and risk appetite aligned.
- Do not exceed predefined drawdown limits when adding tactical complexity.
