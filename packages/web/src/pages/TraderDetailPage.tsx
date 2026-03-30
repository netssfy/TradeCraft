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

export default function TraderDetailPage() {
  const { tx } = useI18n();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [trader, setTrader] = useState<Trader | null>(null);
  const [strategyFiles, setStrategyFiles] = useState<StrategyFile[]>([]);
  const [tradeRuns, setTradeRuns] = useState<TradeRuns | null>(null);

  const [mode, setMode] = useState<Mode>('paper');
  const [selectedBacktestRunId, setSelectedBacktestRunId] = useState<string | null>(null);
  const [selectedPaperRunId, setSelectedPaperRunId] = useState<string | null>(null);

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
  const [runningBacktest, setRunningBacktest] = useState(false);

  const [showBacktestConfig, setShowBacktestConfig] = useState(false);
  const [backtestStartDate, setBacktestStartDate] = useState('');
  const [backtestEndDate, setBacktestEndDate] = useState('');
  const [backtestStrategyFilename, setBacktestStrategyFilename] = useState('');

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
    const active = strategyFiles.find((s) => s.is_active)?.filename ?? '';
    setBacktestStrategyFilename((prev) => prev || active);
    setShowBacktestConfig(true);
  };

  const activeRunId = mode === 'backtest' ? selectedBacktestRunId : selectedPaperRunId;

  const refreshRuns = async (traderId: string) => {
    const runs = await api.listTradeRuns(traderId);
    setTradeRuns(runs);

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
    setBacktestStrategyFilename((prev) => {
      if (prev && files.some((f) => f.filename === prev)) return prev;
      return active;
    });
    return files;
  };

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    setError(null);

    Promise.all([api.getTrader(id), refreshRuns(id), refreshStrategyFiles(id)])
      .then(([loadedTrader, runs]) => {
        setTrader(loadedTrader);
        setBacktestStrategyFilename((prev) => prev || loadedTrader.active_strategy || '');
        if (runs.backtest.length > 0 && runs.paper.length === 0) setMode('backtest');
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;

    if (mode === 'backtest' && !selectedBacktestRunId) {
      setPortfolio(null);
      setPortfolioError(tx('未选择回测运行。', 'No backtest run selected.'));
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
        setPortfolioError(null);
        setReportError(null);
      })
      .catch((e: Error) => {
        if (e.message.includes('404')) {
          setPortfolio(null);
          setTrades([]);
          setBacktestReport(null);
          setPortfolioError(tx('当前选择的运行暂无数据。', 'No data for current run.'));
          return;
        }
        setPortfolioError(e.message);
        setTrades([]);
        setBacktestReport(null);
        setReportError(mode === 'backtest' ? e.message : null);
      })
      .finally(() => setDataLoading(false));
  }, [id, mode, selectedBacktestRunId, selectedPaperRunId, activeRunId]);

  useEffect(() => {
    setTradesPage(1);
  }, [mode, activeRunId, trades]);

  const handleDelete = async () => {
    if (!id || !window.confirm(tx('确定要永久删除该交易员吗？', 'Delete this trader permanently?'))) return;
    setDeleting(true);
    try {
      await api.deleteTrader(id);
      navigate('/');
    } catch (e: any) {
      setError(`${tx('删除失败', 'Delete failed')}: ${e.message}`);
      setDeleting(false);
    }
  };

  const handleRunBacktest = async (startDate: string, endDate: string, strategyFilename: string) => {
    if (!id) return;
    if (startDate > endDate) {
      setError(tx('回测开始日期不能晚于结束日期。', 'Backtest start date must not be later than end date.'));
      return;
    }
    if (!strategyFilename) {
      setError(tx('请选择一个策略用于回测。', 'Please select one strategy for backtest.'));
      return;
    }

    setRunningBacktest(true);
    setError(null);

    try {
      const result = await api.runBacktest(id, {
        start_date: startDate,
        end_date: endDate,
        strategy_filename: strategyFilename,
      });

      await refreshRuns(id);
      setMode('backtest');
      setSelectedBacktestRunId(result.run_id);
      setShowBacktestConfig(false);
    } catch (e: any) {
      setError(`${tx('启动回测失败', 'Failed to start backtest')}: ${e.message}`);
    } finally {
      setRunningBacktest(false);
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
          {tx('返回列表', 'Back to list')}
        </Link>
      </div>
    );
  }

  if (!trader) return null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Link to="/" style={{ color: 'var(--text-muted)', fontSize: 13 }}>{tx('返回列表', 'Back to list')}</Link>
          <h1 style={{ fontSize: 24, fontWeight: 600, marginTop: 8 }}>{trader.id}</h1>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={openBacktestConfig} disabled={runningBacktest}>
            {runningBacktest ? tx('回测中...', 'Running...') : tx('启动回测', 'Run Backtest')}
          </button>
          <button className="btn" onClick={() => setShowEdit(true)}>{tx('编辑', 'Edit')}</button>
          <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? tx('删除中...', 'Deleting...') : tx('删除', 'Delete')}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 24 }}>
        <div className="card">
          <div className="label">{tx('基础信息', 'Basics')}</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('市场', 'Market')}</span>
              <div><span className="badge badge-yellow">{trader.market}</span></div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('初始资金', 'Initial Cash')}</span>
              <div className="mono">{formatCurrency(trader.initial_cash)}</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('手续费率', 'Commission Rate')}</span>
              <div className="mono">{(trader.commission_rate * 100).toFixed(2)}%</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('订单超时', 'Order Timeout')}</span>
              <div className="mono">{trader.order_timeout_seconds}s</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="label">{tx('六维特质', 'Traits')}</div>
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
          <TraderStrategySection traderId={trader.id} onUpdate={handleStrategyUpdate} />
          <TraderDataScopeSection
            mode={mode}
            tradeRuns={tradeRuns}
            selectedBacktestRunId={selectedBacktestRunId}
            selectedPaperRunId={selectedPaperRunId}
            onModeChange={setMode}
            onBacktestRunChange={setSelectedBacktestRunId}
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
              <div className="label" style={{ marginBottom: 12 }}>{tx('回测报告', 'Backtest Report')}</div>
              {dataLoading ? (
                <LoadingSpinner />
              ) : reportError ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>{reportError}</div>
              ) : backtestReport ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('回测区间', 'Backtest Range')}</div>
                    <div className="mono">{shortDate(backtestReport.backtest_start)} ~ {shortDate(backtestReport.backtest_end)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('最终净值', 'Final NAV')}</div>
                    <div className="mono">{formatCurrency(backtestReport.final_nav)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('年化收益率', 'Annualized Return')}</div>
                    <div className="mono">{formatPercent(backtestReport.metrics.annualized_return)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('最大回撤', 'Max Drawdown')}</div>
                    <div className="mono">{formatPercent(backtestReport.metrics.max_drawdown)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('夏普比率', 'Sharpe Ratio')}</div>
                    <div className="mono">{backtestReport.metrics.sharpe_ratio.toFixed(3)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('胜率', 'Win Rate')}</div>
                    <div className="mono">{formatPercent(backtestReport.metrics.win_rate)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{tx('盈亏比', 'Profit/Loss Ratio')}</div>
                    <div className="mono">{backtestReport.metrics.profit_loss_ratio.toFixed(3)}</div>
                  </div>
                </div>
              ) : (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>{tx('当前回测暂无报告。', 'No report for current backtest.')}</div>
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
            <div className="label" style={{ marginBottom: 12 }}>{tx('启动回测', 'Run Backtest')}</div>
            <div style={{ display: 'grid', gap: 12 }}>
              <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {tx('开始日期', 'Start Date')}
                <input type="date" value={backtestStartDate} onChange={(e) => setBacktestStartDate(e.target.value)} style={{ width: '100%', marginTop: 6 }} />
              </label>
              <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {tx('结束日期', 'End Date')}
                <input type="date" value={backtestEndDate} onChange={(e) => setBacktestEndDate(e.target.value)} style={{ width: '100%', marginTop: 6 }} />
              </label>
              <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {tx('回测策略', 'Backtest Strategy')}
                <select value={backtestStrategyFilename} onChange={(e) => setBacktestStrategyFilename(e.target.value)} style={{ width: '100%', marginTop: 6 }}>
                  {strategyFiles.length === 0 ? (
                    <option value="">{tx('暂无可用策略', 'No available strategy')}</option>
                  ) : (
                    strategyFiles.map((s) => (
                      <option key={s.filename} value={s.filename}>
                        {s.filename}
                        {s.is_active ? ` (${tx('激活中', 'Active')})` : ''}
                      </option>
                    ))
                  )}
                </select>
              </label>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <button className="btn" onClick={() => setShowBacktestConfig(false)} disabled={runningBacktest}>{tx('取消', 'Cancel')}</button>
              <button
                className="btn btn-primary"
                onClick={() => handleRunBacktest(backtestStartDate, backtestEndDate, backtestStrategyFilename)}
                disabled={runningBacktest || strategyFiles.length === 0 || !backtestStrategyFilename}
              >
                {runningBacktest ? tx('回测中...', 'Running...') : tx('确认', 'Confirm')}
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
