import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import type { BacktestReport, Portfolio, StrategyFile, Trade, TradeRuns, Trader } from '@tradecraft/shared/types';
import { TRAIT_LABELS, formatCurrency } from '@tradecraft/shared/utils';
import EditTraderModal from '../components/EditTraderModal';
import ErrorMessage from '../components/ErrorMessage';
import LoadingSpinner from '../components/LoadingSpinner';
import TraderDataScopeSection from '../components/TraderDataScopeSection';
import TraderPortfolioSection from '../components/TraderPortfolioSection';
import TraderPositionsSection from '../components/TraderPositionsSection';
import TraderStrategySection from '../components/TraderStrategySection';
import TraderTradesSection from '../components/TraderTradesSection';
import { useI18n } from '../hooks/useI18n';
import { api } from '../services/api';

type Mode = 'paper' | 'backtest';

const TRADES_PAGE_SIZE = 20;

function matchRunByStrategy(report: BacktestReport | null | undefined, strategyFilename: string | null): boolean {
  if (!strategyFilename) return true;
  return (report?.strategy_filename ?? null) === strategyFilename;
}

export default function TraderDetailPage() {
  const { tx } = useI18n();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [trader, setTrader] = useState<Trader | null>(null);
  const [strategyFiles, setStrategyFiles] = useState<StrategyFile[]>([]);
  const [tradeRuns, setTradeRuns] = useState<TradeRuns | null>(null);
  const [backtestRunReports, setBacktestRunReports] = useState<Record<string, BacktestReport | null>>({});

  const [mode, setMode] = useState<Mode>('paper');
  const [selectedBacktestRunId, setSelectedBacktestRunId] = useState<string | null>(null);
  const [selectedPaperRunId, setSelectedPaperRunId] = useState<string | null>(null);
  const [selectedBacktestStrategyFilename, setSelectedBacktestStrategyFilename] = useState<string | null>(null);

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [trades, setTrades] = useState<Trade[] | null>(null);
  const [backtestReport, setBacktestReport] = useState<BacktestReport | null>(null);
  const [tradesPage, setTradesPage] = useState(1);

  const [loading, setLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const [showEdit, setShowEdit] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletingBacktestRunId, setDeletingBacktestRunId] = useState<string | null>(null);
  const [runningBacktest, setRunningBacktest] = useState(false);

  const [showBacktestConfig, setShowBacktestConfig] = useState(false);
  const [backtestStartDate, setBacktestStartDate] = useState('');
  const [backtestEndDate, setBacktestEndDate] = useState('');
  const [backtestStrategyFilenames, setBacktestStrategyFilenames] = useState<string[]>([]);

  const formatDateInput = (d: Date) => d.toISOString().slice(0, 10);

  const getDefaultBacktestRange = () => {
    const end = new Date();
    const start = new Date(end);
    start.setMonth(start.getMonth() - 3);
    return {
      start: formatDateInput(start),
      end: formatDateInput(end),
    };
  };

  const openBacktestConfig = () => {
    const range = getDefaultBacktestRange();
    setBacktestStartDate(range.start);
    setBacktestEndDate(range.end);
    const active = strategyFiles.find((s) => s.is_active)?.filename;
    setBacktestStrategyFilenames((prev) => {
      const validPrevious = prev.filter((filename) => strategyFiles.some((s) => s.filename === filename));
      if (validPrevious.length > 0) return validPrevious;
      return active ? [active] : [];
    });
    setShowBacktestConfig(true);
  };

  const toggleBacktestStrategy = (filename: string) => {
    setBacktestStrategyFilenames((prev) => (
      prev.includes(filename) ? prev.filter((name) => name !== filename) : [...prev, filename]
    ));
  };

  const activeRunId = mode === 'backtest' ? selectedBacktestRunId : selectedPaperRunId;

  const loadBacktestRunReports = async (traderId: string, runIds: string[]) => {
    const reportEntries = await Promise.all(
      runIds.map(async (runId) => {
        try {
          const report = await api.getBacktestReport(traderId, runId);
          return [runId, report] as const;
        } catch (e: any) {
          if (String(e?.message || '').includes('404')) return [runId, null] as const;
          throw e;
        }
      })
    );

    return Object.fromEntries(reportEntries);
  };

  const refreshRuns = async (traderId: string) => {
    const runs = await api.listTradeRuns(traderId);
    setTradeRuns(runs);

    const reports = await loadBacktestRunReports(traderId, runs.backtest);
    setBacktestRunReports(reports);

    const latestPaper = runs.paper.length > 0 ? runs.paper[runs.paper.length - 1] : null;
    const latestBacktest = runs.backtest.length > 0 ? runs.backtest[runs.backtest.length - 1] : null;

    setSelectedPaperRunId((prev) => {
      if (prev && runs.paper.includes(prev)) return prev;
      return latestPaper;
    });

    setSelectedBacktestRunId((prev) => {
      if (prev && runs.backtest.includes(prev)) return prev;
      return latestBacktest;
    });

    return runs;
  };

  const refreshStrategyFiles = async (traderId: string) => {
    const files = await api.listStrategies(traderId);
    setStrategyFiles(files);

    const active = files.find((s) => s.is_active)?.filename ?? '';
    setSelectedBacktestStrategyFilename((prev) => {
      if (prev === null) return null;
      if (prev && files.some((f) => f.filename === prev)) return prev;
      return active || null;
    });

    return files;
  };

  const backtestStrategyOptions = useMemo(() => {
    const fromFiles = strategyFiles.map((s) => s.filename);
    const fromReports = Object.values(backtestRunReports)
      .map((report) => report?.strategy_filename ?? null)
      .filter((filename): filename is string => Boolean(filename));
    return Array.from(new Set([...fromFiles, ...fromReports]));
  }, [strategyFiles, backtestRunReports]);

  const filteredBacktestRunIds = useMemo(() => {
    if (!tradeRuns) return [];
    return tradeRuns.backtest.filter((runId) =>
      matchRunByStrategy(backtestRunReports[runId], selectedBacktestStrategyFilename)
    );
  }, [tradeRuns, backtestRunReports, selectedBacktestStrategyFilename]);

  useEffect(() => {
    if (!tradeRuns) return;

    setSelectedBacktestRunId((prev) => {
      if (prev && filteredBacktestRunIds.includes(prev)) return prev;
      return filteredBacktestRunIds.length > 0 ? filteredBacktestRunIds[filteredBacktestRunIds.length - 1] : null;
    });
  }, [tradeRuns, filteredBacktestRunIds]);

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    setError(null);

    Promise.all([api.getTrader(id), refreshRuns(id), refreshStrategyFiles(id)])
      .then(([loadedTrader, runs]) => {
        setTrader(loadedTrader);
        setSelectedBacktestStrategyFilename((prev) => prev ?? (loadedTrader.active_strategy || null));
        if (runs.backtest.length > 0 && runs.paper.length === 0) setMode('backtest');
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    setBacktestStrategyFilenames((prev) => prev.filter((filename) => strategyFiles.some((s) => s.filename === filename)));
  }, [strategyFiles]);

  useEffect(() => {
    if (!id) return;

    if (mode === 'backtest' && !selectedBacktestRunId) {
      setPortfolio(null);
      setPortfolioError(tx('No backtest run selected.', 'No backtest run selected.'));
      setTrades([]);
      setBacktestReport(null);
      setReportError(null);
      return;
    }

    setDataLoading(true);
    setPortfolioError(null);
    setReportError(null);

    const portfolioPromise = api.getPortfolio(id, mode, mode === 'backtest' ? selectedBacktestRunId ?? undefined : undefined);
    const tradesPromise = activeRunId ? api.getTrades(id, mode, activeRunId) : Promise.resolve([] as Trade[]);
    const reportPromise =
      mode === 'backtest' && selectedBacktestRunId
        ? api.getBacktestReport(id, selectedBacktestRunId).catch((e: Error) => {
            if (e.message.includes('404')) return null;
            throw e;
          })
        : Promise.resolve(null as BacktestReport | null);

    Promise.all([portfolioPromise, tradesPromise, reportPromise])
      .then(([loadedPortfolio, loadedTrades, loadedReport]) => {
        setPortfolio(loadedPortfolio);
        setTrades(loadedTrades);
        setBacktestReport(loadedReport);
        if (mode === 'backtest' && selectedBacktestRunId) {
          setBacktestRunReports((prev) => ({
            ...prev,
            [selectedBacktestRunId]: loadedReport,
          }));
        }
        setPortfolioError(null);
        setReportError(null);
      })
      .catch((e: Error) => {
        if (e.message.includes('404')) {
          setPortfolio(null);
          setTrades([]);
          setBacktestReport(null);
          if (mode === 'backtest' && selectedBacktestRunId) {
            setBacktestRunReports((prev) => ({
              ...prev,
              [selectedBacktestRunId]: null,
            }));
          }
          setPortfolioError(tx('No data for current run.', 'No data for current run.'));
          return;
        }
        setPortfolioError(e.message);
        setTrades([]);
        setBacktestReport(null);
        setReportError(mode === 'backtest' ? e.message : null);
      })
      .finally(() => setDataLoading(false));
  }, [id, mode, selectedBacktestRunId, selectedPaperRunId, activeRunId, tx]);

  useEffect(() => {
    setTradesPage(1);
  }, [mode, activeRunId, trades]);

  const handleDelete = async () => {
    if (!id || !window.confirm(tx('Delete this trader permanently?', 'Delete this trader permanently?'))) return;
    setDeleting(true);
    try {
      await api.deleteTrader(id);
      navigate('/');
    } catch (e: any) {
      setError(`${tx('Delete failed', 'Delete failed')}: ${e.message}`);
      setDeleting(false);
    }
  };

  const handleRunBacktest = async (startDate: string, endDate: string, strategyFilenames: string[]) => {
    if (!id) return;
    if (startDate > endDate) {
      setError(tx('Backtest start date must not be later than end date.', 'Backtest start date must not be later than end date.'));
      return;
    }
    if (strategyFilenames.length === 0) {
      setError(tx('Please select at least one strategy for backtest.', 'Please select at least one strategy for backtest.'));
      return;
    }

    setRunningBacktest(true);
    setError(null);

    try {
      const result = await api.runBacktest(id, {
        start_date: startDate,
        end_date: endDate,
        strategy_list: strategyFilenames,
      });

      await refreshRuns(id);
      setMode('backtest');
      setSelectedBacktestStrategyFilename((prev) => {
        if (prev && strategyFilenames.includes(prev)) return prev;
        return strategyFilenames[0] ?? null;
      });
      const latestRunId = result.runs?.length ? result.runs[result.runs.length - 1]?.run_id : result.run_id;
      if (latestRunId) setSelectedBacktestRunId(latestRunId);
      setShowBacktestConfig(false);
    } catch (e: any) {
      setError(`${tx('Failed to start backtest', 'Failed to start backtest')}: ${e.message}`);
    } finally {
      setRunningBacktest(false);
    }
  };

  const handleDeleteBacktestRun = async (runId: string) => {
    if (!id) return;
    if (!window.confirm(tx('Delete this backtest run?', 'Delete this backtest run?'))) return;

    setDeletingBacktestRunId(runId);
    setError(null);
    try {
      await api.deleteBacktestRun(id, runId);
      await refreshRuns(id);
      if (selectedBacktestRunId === runId) {
        setBacktestReport(null);
      }
    } catch (e: any) {
      setError(`${tx('Failed to delete backtest run', 'Failed to delete backtest run')}: ${e.message}`);
    } finally {
      setDeletingBacktestRunId(null);
    }
  };

  const totalTradePages = useMemo(() => {
    if (!trades || trades.length === 0) return 1;
    return Math.max(1, Math.ceil(trades.length / TRADES_PAGE_SIZE));
  }, [trades]);

  const pagedTrades = useMemo(() => {
    if (!trades || trades.length === 0) return [];
    const start = (tradesPage - 1) * TRADES_PAGE_SIZE;
    return trades.slice(start, start + TRADES_PAGE_SIZE);
  }, [trades, tradesPage]);

  const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;
  const shortDate = (value: string) => value.split('T')[0] || value;
  const handleStrategyUpdate = () => {
    if (!trader) return Promise.resolve();
    return Promise.all([api.getTrader(trader.id).then(setTrader), refreshStrategyFiles(trader.id)]).then(() => undefined);
  };

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div>
        <ErrorMessage message={error} />
        <Link to="/" className="btn" style={{ marginTop: 16 }}>
          {tx('Back to list', 'Back to list')}
        </Link>
      </div>
    );
  }

  if (!trader) return null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Link to="/" style={{ color: 'var(--text-muted)', fontSize: 13 }}>{tx('Back to list', 'Back to list')}</Link>
          <h1 style={{ fontSize: 24, fontWeight: 600, marginTop: 8 }}>{trader.id}</h1>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" onClick={() => setShowEdit(true)}>{tx('Edit', 'Edit')}</button>
          <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? tx('Deleting...', 'Deleting...') : tx('Delete', 'Delete')}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 24 }}>
        <div className="card">
          <div className="label">{tx('Basics', 'Basics')}</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Market', 'Market')}</span>
              <div><span className="badge badge-yellow">{trader.market}</span></div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Initial Cash', 'Initial Cash')}</span>
              <div className="mono">{formatCurrency(trader.initial_cash)}</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Commission Rate', 'Commission Rate')}</span>
              <div className="mono">{(trader.commission_rate * 100).toFixed(2)}%</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Order Timeout', 'Order Timeout')}</span>
              <div className="mono">{trader.order_timeout_seconds}s</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="label">{tx('Traits', 'Traits')}</div>
          <div style={{ marginTop: 8 }}>
            {Object.entries(trader.traits).map(([key, value]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{TRAIT_LABELS[key] || key}</span>
                <span style={{ fontSize: 13 }}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="trader-detail-layout">
        <aside className="trader-detail-sidebar">
          <TraderStrategySection
            traderId={trader.id}
            onUpdate={handleStrategyUpdate}
            onRunBacktest={openBacktestConfig}
            runningBacktest={runningBacktest}
          />
          <TraderDataScopeSection
            mode={mode}
            backtestRuns={filteredBacktestRunIds}
            backtestRunReports={backtestRunReports}
            backtestStrategyOptions={backtestStrategyOptions}
            selectedBacktestStrategyFilename={selectedBacktestStrategyFilename}
            selectedBacktestRunId={selectedBacktestRunId}
            selectedPaperRunId={selectedPaperRunId}
            deletingBacktestRunId={deletingBacktestRunId}
            onModeChange={setMode}
            onBacktestStrategyChange={setSelectedBacktestStrategyFilename}
            onBacktestRunChange={setSelectedBacktestRunId}
            onDeleteBacktestRun={handleDeleteBacktestRun}
          />
        </aside>

        <section className="trader-detail-main">
          <TraderPortfolioSection
            mode={mode}
            selectedBacktestRunId={selectedBacktestRunId}
            dataLoading={dataLoading}
            portfolioError={portfolioError}
            portfolio={portfolio}
            initialCash={trader.initial_cash}
          />

          {mode === 'backtest' && (
            <div className="card">
              <div className="label" style={{ marginBottom: 12 }}>{tx('Backtest Report', 'Backtest Report')}</div>
              {dataLoading ? (
                <LoadingSpinner />
              ) : reportError ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>{reportError}</div>
              ) : backtestReport ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Backtest Range', 'Backtest Range')}</div>
                    <div className="mono">{shortDate(backtestReport.backtest_start)} ~ {shortDate(backtestReport.backtest_end)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Final NAV', 'Final NAV')}</div>
                    <div className="mono">{formatCurrency(backtestReport.final_nav)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Annualized Return', 'Annualized Return')}</div>
                    <div className="mono">{formatPercent(backtestReport.metrics.annualized_return)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Max Drawdown', 'Max Drawdown')}</div>
                    <div className="mono">{formatPercent(backtestReport.metrics.max_drawdown)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Sharpe Ratio', 'Sharpe Ratio')}</div>
                    <div className="mono">{backtestReport.metrics.sharpe_ratio.toFixed(3)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Win Rate', 'Win Rate')}</div>
                    <div className="mono">{formatPercent(backtestReport.metrics.win_rate)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('Profit/Loss Ratio', 'Profit/Loss Ratio')}</div>
                    <div className="mono">{backtestReport.metrics.profit_loss_ratio.toFixed(3)}</div>
                  </div>
                </div>
              ) : (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>{tx('No report for current backtest.', 'No report for current backtest.')}</div>
              )}
            </div>
          )}

          <TraderPositionsSection portfolio={portfolio} portfolioError={portfolioError} />

          <TraderTradesSection
            trades={trades}
            pagedTrades={pagedTrades}
            tradesPage={tradesPage}
            totalTradePages={totalTradePages}
            dataLoading={dataLoading}
            onPrevPage={() => setTradesPage((p) => Math.max(1, p - 1))}
            onNextPage={() => setTradesPage((p) => Math.min(totalTradePages, p + 1))}
          />
        </section>
      </div>

      {showBacktestConfig && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div className="card" style={{ width: '100%', maxWidth: 420 }}>
            <div className="label" style={{ marginBottom: 12 }}>{tx('Run Backtest', 'Run Backtest')}</div>
            <div style={{ display: 'grid', gap: 12 }}>
              <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {tx('Start Date', 'Start Date')}
                <input type="date" value={backtestStartDate} onChange={(e) => setBacktestStartDate(e.target.value)} style={{ width: '100%', marginTop: 6 }} />
              </label>
              <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {tx('End Date', 'End Date')}
                <input type="date" value={backtestEndDate} onChange={(e) => setBacktestEndDate(e.target.value)} style={{ width: '100%', marginTop: 6 }} />
              </label>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                <div style={{ marginBottom: 6 }}>{tx('Backtest Strategies', 'Backtest Strategies')}</div>
                <div style={{ border: '1px solid var(--border-color)', borderRadius: 10, overflow: 'hidden' }}>
                  {strategyFiles.length === 0 ? (
                    <div style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{tx('No available strategy', 'No available strategy')}</div>
                  ) : (
                    strategyFiles.map((s) => {
                      const selected = backtestStrategyFilenames.includes(s.filename);
                      return (
                        <label
                          key={s.filename}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            padding: '10px 12px',
                            borderTop: '1px solid var(--border-color)',
                            background: selected ? 'rgba(59, 130, 246, 0.18)' : 'transparent',
                            cursor: 'pointer',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={() => toggleBacktestStrategy(s.filename)}
                          />
                          <span className="mono" style={{ flex: 1 }}>{s.filename}</span>
                          {s.is_active && <span className="badge badge-green">{tx('Active', 'Active')}</span>}
                        </label>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <button className="btn" onClick={() => setShowBacktestConfig(false)} disabled={runningBacktest}>{tx('Cancel', 'Cancel')}</button>
              <button
                className="btn btn-primary"
                onClick={() => handleRunBacktest(backtestStartDate, backtestEndDate, backtestStrategyFilenames)}
                disabled={runningBacktest || strategyFiles.length === 0 || backtestStrategyFilenames.length === 0}
              >
                {runningBacktest ? tx('Running...', 'Running...') : tx('Confirm', 'Confirm')}
              </button>
            </div>
          </div>
        </div>
      )}

      {showEdit && (
        <EditTraderModal
          trader={trader}
          onClose={() => setShowEdit(false)}
          onUpdated={(updated) => {
            setTrader(updated);
            setShowEdit(false);
          }}
        />
      )}
    </div>
  );
}
