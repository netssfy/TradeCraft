# Auto Quant Trainer Program (v1)

This program defines an autoresearch-style closed loop for strategy R&D in TradeCraft.
The agent owns execution end-to-end: research, implementation, backtest, comparison, and iteration.

## Objective and Constants

- `MAX_ITERATIONS = 10`
- `TRADER_DIR = backend/data/traders/{TRADER_ID}`
- `OBJECTIVE_FILE = {TRADER_DIR}/references/metrics.json`
- `STRATEGY_DIR = {TRADER_DIR}/strategy`
- `STRATEGY_INTERFACE = backend/app/trading/strategy.py`

Read `OBJECTIVE_FILE` once at the start of each iteration and treat its target values as immutable.
Do not edit or regenerate `OBJECTIVE_FILE`.

## Required Tooling

Run commands from `backend/`.

- Data access:
  - `python -m app.cli data availability`
  - `python -m app.cli data slice --market <MARKET> --symbol <SYMBOL> --interval <INTERVAL> --start <START> --end <END>`
  - `python -m app.cli data file --market <MARKET> --symbol <SYMBOL> --interval <INTERVAL> --period <YYYY-MM>`
- Backtest:
  - `python -m app.cli backtest run --trader-id <TRADER_ID> --start-date <START> --end-date <END>`
  - `python -m app.cli backtest report --trader-id <TRADER_ID> --run-id <RUN_ID>`

Internet research is allowed and expected for target-instrument context.
Temporary Python scripts are allowed for local analysis.

## Loop Protocol

For `iteration` from 1 to `MAX_ITERATIONS`:

1. Load constraints and baseline.
- Read `OBJECTIVE_FILE`.
- Read latest strategy in `STRATEGY_DIR`.
- Read last available backtest report if any.

2. Form one concrete hypothesis.
- Define one main change to test.
- Keep change set focused and explainable.

3. Gather evidence.
- Use CLI data commands to inspect local price/volume structure.
- Use internet research for regime/event context when relevant.
- Optionally run temporary Python analysis.

4. Implement candidate strategy.
- Create or update one strategy file in `STRATEGY_DIR`.
- Ensure strategy imports and subclasses `Strategy` from `STRATEGY_INTERFACE`.
- Ensure methods `initialize` and `on_bar` exist and are valid.

5. Run backtest via CLI.
- Execute one backtest with defined date window.
- Capture `run_id`, report metrics, and key trade diagnostics.

6. Compare against objective.
- Compare report metrics with thresholds from `OBJECTIVE_FILE`.
- Mark status:
  - `PASS` if all required objective conditions are met.
  - `FAIL` otherwise.

7. Decide.
- If `PASS`, stop and keep strategy as current winner.
- If `FAIL`, record why and continue to next iteration.

## Output Contract Per Iteration

Write/update a concise research log in `{TRADER_DIR}/references/research_log.md` with:

- Iteration number
- Hypothesis
- Code change summary
- Backtest command used
- Backtest `run_id`
- Metrics snapshot
- Objective comparison (`PASS` or `FAIL`)
- Next-step decision

## Termination Rules

- Stop immediately when objectives are met.
- Stop at iteration 10 even if objectives are not met.
- On failure after 10 iterations, keep the best observed strategy and report remaining gaps versus objective.

