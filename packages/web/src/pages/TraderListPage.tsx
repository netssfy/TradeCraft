import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Portfolio, TradeRuns, Trader } from '@tradecraft/shared/types';
import { api } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { TRAIT_LABELS, formatCurrency } from '@tradecraft/shared/utils';

interface CombinationResult {
  id: string;
  label: string;
  returnPct: number | null;
}

interface TraderRowData {
  trader: Trader;
  strategyNames: string[];
  combinations: CombinationResult[];
  paperReturn: number | null;
}

function getSnapshotReturn(portfolio: Portfolio | null, initialCash: number): number | null {
  if (!portfolio || portfolio.snapshots.length === 0 || initialCash === 0) {
    return null;
  }

  const last = portfolio.snapshots[portfolio.snapshots.length - 1];
  const totalValue =
    last.cash + Object.values(last.positions).reduce((sum, p) => sum + p.quantity * p.avg_cost, 0);

  return ((totalValue - initialCash) / initialCash) * 100;
}

function formatReturn(value: number | null): string {
  if (value === null || Number.isNaN(value)) return 'N/A';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function buildBacktestCombinationIds(runs: TradeRuns | null): string[] {
  if (!runs) return [];
  return runs.backtest.slice(-4).reverse();
}

export default function TraderListPage() {
  const [rows, setRows] = useState<TraderRowData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);

      try {
        const traders = await api.listTraders();
        const list = await Promise.all(
          traders.map(async (trader): Promise<TraderRowData> => {
            const [strategies, runs, paperPortfolio] = await Promise.all([
              api.listStrategies(trader.id).catch(() => []),
              api.listTradeRuns(trader.id).catch(() => null),
              api.getPortfolio(trader.id, 'paper').catch(() => null),
            ]);

            const paperReturn = getSnapshotReturn(paperPortfolio, trader.initial_cash);
            const backtestIds = buildBacktestCombinationIds(runs);

            const backtestReturns = await Promise.all(
              backtestIds.map(async (runId) => {
                const portfolio = await api.getPortfolio(trader.id, 'backtest', runId).catch(() => null);

                return {
                  id: runId,
                  label: `backtest:${runId}`,
                  returnPct: getSnapshotReturn(portfolio, trader.initial_cash),
                };
              })
            );

            return {
              trader,
              strategyNames: strategies.map((item) => item.filename),
              combinations: [{ id: 'paper', label: 'paper', returnPct: paperReturn }, ...backtestReturns],
              paperReturn,
            };
          })
        );

        list.sort((a, b) => {
          if (a.paperReturn === null && b.paperReturn === null) return 0;
          if (a.paperReturn === null) return 1;
          if (b.paperReturn === null) return -1;
          return b.paperReturn - a.paperReturn;
        });

        if (!cancelled) {
          setRows(list);
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(e.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={`Load failed: ${error}`} />;

  if (rows.length === 0) {
    return (
      <div className="empty-state">
        <h3>No traders yet</h3>
        <p style={{ marginBottom: 16 }}>Create your first AI trader to begin.</p>
        <Link to="/traders/create" className="btn btn-primary">
          Create trader
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600 }}>Trader List</h1>
        <Link to="/traders/create" className="btn btn-primary">
          + Create trader
        </Link>
      </div>

      <div className="trader-table">
        <div className="trader-table-head">
          <div>Trader</div>
          <div>Traits</div>
          <div>Strategies</div>
          <div>Combinations</div>
        </div>

        {rows.map(({ trader, strategyNames, combinations, paperReturn }) => (
          <div key={trader.id} className="trader-row">
            <div className="trader-cell">
              <Link to={`/traders/${trader.id}`} style={{ fontWeight: 700, fontSize: 16 }}>
                {trader.id}
              </Link>

              <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                <span className="badge badge-yellow">{trader.market}</span>
                <span className={`badge ${paperReturn !== null && paperReturn >= 0 ? 'badge-green' : 'badge-red'}`}>
                  paper {formatReturn(paperReturn)}
                </span>
              </div>

              <div style={{ marginTop: 8, color: 'var(--text-muted)', fontSize: 12 }}>
                Initial cash: <span className="mono">{formatCurrency(trader.initial_cash)}</span>
              </div>
            </div>

            <div className="trader-cell">
              <div className="trader-chip-wrap">
                {Object.entries(trader.traits).map(([key, value]) => (
                  <span key={key} className="trader-chip">
                    {TRAIT_LABELS[key] || key}: {value}
                  </span>
                ))}
              </div>
            </div>

            <div className="trader-cell">
              {strategyNames.length === 0 ? (
                <span style={{ color: 'var(--text-muted)' }}>No strategy</span>
              ) : (
                <div className="strategy-scroll-list">
                  {strategyNames.map((name) => (
                    <div key={name} className="strategy-item mono">
                      {name}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="trader-cell">
              <div className="trader-chip-wrap">
                {combinations.map((combo) => (
                  <span
                    key={combo.id}
                    className={`badge ${combo.returnPct !== null && combo.returnPct >= 0 ? 'badge-green' : 'badge-red'}`}
                  >
                    {combo.label} {formatReturn(combo.returnPct)}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
