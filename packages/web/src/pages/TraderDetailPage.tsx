import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import type { Portfolio, Trade, TradeRuns, Trader } from '@tradecraft/shared/types';
import { TRAIT_LABELS, formatCurrency } from '@tradecraft/shared/utils';
import EditTraderModal from '../components/EditTraderModal';
import ErrorMessage from '../components/ErrorMessage';
import LoadingSpinner from '../components/LoadingSpinner';
import PortfolioChart from '../components/PortfolioChart';
import StrategyManager from '../components/StrategyManager';
import { api } from '../services/api';

type Mode = 'paper' | 'backtest';

const TRADES_PAGE_SIZE = 20;

export default function TraderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [trader, setTrader] = useState<Trader | null>(null);
  const [tradeRuns, setTradeRuns] = useState<TradeRuns | null>(null);

  const [mode, setMode] = useState<Mode>('paper');
  const [selectedBacktestRunId, setSelectedBacktestRunId] = useState<string | null>(null);
  const [selectedPaperRunId, setSelectedPaperRunId] = useState<string | null>(null);

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [trades, setTrades] = useState<Trade[] | null>(null);
  const [tradesPage, setTradesPage] = useState(1);

  const [loading, setLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);

  const [showEdit, setShowEdit] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [runningBacktest, setRunningBacktest] = useState(false);

  const [showBacktestConfig, setShowBacktestConfig] = useState(false);
  const [backtestStartDate, setBacktestStartDate] = useState('');
  const [backtestEndDate, setBacktestEndDate] = useState('');

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

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    setError(null);

    Promise.all([api.getTrader(id), refreshRuns(id)])
      .then(([loadedTrader, runs]) => {
        setTrader(loadedTrader);
        if (runs.backtest.length > 0 && runs.paper.length === 0) {
          setMode('backtest');
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;

    if (mode === 'backtest' && !selectedBacktestRunId) {
      setPortfolio(null);
      setPortfolioError('未选择回测运行。');
      setTrades([]);
      return;
    }

    setDataLoading(true);
    setPortfolioError(null);

    const portfolioPromise = api.getPortfolio(
      id,
      mode,
      mode === 'backtest' ? selectedBacktestRunId ?? undefined : undefined
    );

    const tradesPromise = activeRunId
      ? api.getTrades(id, mode, activeRunId)
      : Promise.resolve([] as Trade[]);

    Promise.all([portfolioPromise, tradesPromise])
      .then(([loadedPortfolio, loadedTrades]) => {
        setPortfolio(loadedPortfolio);
        setTrades(loadedTrades);
        setPortfolioError(null);
      })
      .catch((e: Error) => {
        if (e.message.includes('404')) {
          setPortfolio(null);
          setTrades([]);
          setPortfolioError('当前选择的运行暂无数据。');
          return;
        }
        setPortfolioError(e.message);
        setTrades([]);
      })
      .finally(() => setDataLoading(false));
  }, [id, mode, selectedBacktestRunId, selectedPaperRunId, activeRunId]);

  useEffect(() => {
    setTradesPage(1);
  }, [mode, activeRunId, trades]);

  const handleDelete = async () => {
    if (!id || !window.confirm('确定要永久删除该交易员吗？')) return;
    setDeleting(true);
    try {
      await api.deleteTrader(id);
      navigate('/');
    } catch (e: any) {
      setError(`删除失败: ${e.message}`);
      setDeleting(false);
    }
  };

  const handleRunBacktest = async (startDate: string, endDate: string) => {
    if (!id) return;
    if (startDate > endDate) {
      setError('回测开始日期不能晚于结束日期。');
      return;
    }

    setRunningBacktest(true);
    setError(null);

    try {
      const result = await api.runBacktest(id, {
        start_date: startDate,
        end_date: endDate,
      });

      await refreshRuns(id);
      setMode('backtest');
      setSelectedBacktestRunId(result.run_id);
      setShowBacktestConfig(false);
    } catch (e: any) {
      setError(`启动回测失败: ${e.message}`);
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

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div>
        <ErrorMessage message={error} />
        <Link to="/" className="btn" style={{ marginTop: 16 }}>
          返回列表
        </Link>
      </div>
    );
  }

  if (!trader) return null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Link to="/" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            返回列表
          </Link>
          <h1 style={{ fontSize: 24, fontWeight: 600, marginTop: 8 }}>{trader.id}</h1>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={openBacktestConfig} disabled={runningBacktest}>
            {runningBacktest ? '回测中...' : '启动回测'}
          </button>
          <button className="btn" onClick={() => setShowEdit(true)}>
            编辑
          </button>
          <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? '删除中...' : '删除'}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 24 }}>
        <div className="card">
          <div className="label">基础信息</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>市场</span>
              <div>
                <span className="badge badge-yellow">{trader.market}</span>
              </div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>初始资金</span>
              <div className="mono">{formatCurrency(trader.initial_cash)}</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>手续费率</span>
              <div className="mono">{(trader.commission_rate * 100).toFixed(2)}%</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>订单超时</span>
              <div className="mono">{trader.order_timeout_seconds}s</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="label">六维特质</div>
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

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <div className="label" style={{ margin: 0 }}>数据范围</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              className={`btn ${mode === 'paper' ? 'btn-primary' : ''}`}
              onClick={() => setMode('paper')}
              style={{ padding: '4px 12px', fontSize: 12 }}
            >
              模拟盘
            </button>
            <button
              className={`btn ${mode === 'backtest' ? 'btn-primary' : ''}`}
              onClick={() => setMode('backtest')}
              style={{ padding: '4px 12px', fontSize: 12 }}
            >
              回测
            </button>
          </div>
        </div>

        {mode === 'backtest' && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>回测 Run ID</div>
            {tradeRuns && tradeRuns.backtest.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {tradeRuns.backtest.map((runId) => (
                  <button
                    key={runId}
                    className={`btn ${selectedBacktestRunId === runId ? 'btn-primary' : ''}`}
                    onClick={() => setSelectedBacktestRunId(runId)}
                    style={{ padding: '4px 8px', fontSize: 12 }}
                  >
                    {runId}
                  </button>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>暂无回测运行记录。</div>
            )}
          </div>
        )}

        {mode === 'paper' && (
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>
            当前模拟盘运行: {selectedPaperRunId || '（无）'}
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="label" style={{ marginBottom: 12 }}>
          收益曲线 ({mode === 'paper' ? '模拟盘' : `回测 ${selectedBacktestRunId || ''}`})
        </div>
        {dataLoading ? (
          <LoadingSpinner />
        ) : portfolioError ? (
          <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>{portfolioError}</div>
        ) : portfolio ? (
          <PortfolioChart portfolio={portfolio} initialCash={trader.initial_cash} />
        ) : (
          <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>暂无数据。</div>
        )}
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="label" style={{ marginBottom: 12 }}>
          持仓快照
        </div>
        {portfolio && portfolio.snapshots.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)' }}>日期</th>
                  <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)' }}>现金</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)' }}>持仓</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.snapshots.slice().reverse().map((snap) => (
                  <tr key={snap.date} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td className="mono" style={{ padding: '8px 12px' }}>{snap.date}</td>
                    <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>{formatCurrency(snap.cash)}</td>
                    <td style={{ padding: '8px 12px' }}>
                      {Object.entries(snap.positions).map(([sym, pos]) => (
                        <span key={sym} style={{ marginRight: 12 }}>
                          {sym}: <span className="mono">{pos.quantity}</span> @ <span className="mono">{formatCurrency(pos.avg_cost)}</span>
                        </span>
                      ))}
                      {Object.keys(snap.positions).length === 0 && (
                        <span style={{ color: 'var(--text-muted)' }}>空仓</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
            {portfolioError || '暂无持仓数据。'}
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="label" style={{ marginBottom: 12 }}>
          成交记录
        </div>

        {trades && trades.length > 0 && (
          <>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)' }}>时间</th>
                    <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)' }}>标的</th>
                    <th style={{ textAlign: 'center', padding: '8px 12px', color: 'var(--text-muted)' }}>方向</th>
                    <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)' }}>数量</th>
                    <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)' }}>价格</th>
                    <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)' }}>手续费</th>
                  </tr>
                </thead>
                <tbody>
                  {pagedTrades.map((trade, i) => (
                    <tr key={`${trade.timestamp}-${trade.symbol}-${i}`} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td className="mono" style={{ padding: '8px 12px' }}>{trade.timestamp}</td>
                      <td style={{ padding: '8px 12px' }}>{trade.symbol}</td>
                      <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                        <span className={`badge ${trade.direction === 'buy' ? 'badge-green' : 'badge-red'}`}>
                          {trade.direction === 'buy' ? '买入' : '卖出'}
                        </span>
                      </td>
                      <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>{trade.quantity}</td>
                      <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>{formatCurrency(trade.price)}</td>
                      <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>{formatCurrency(trade.commission)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                第 {tradesPage} / {totalTradePages} 页（共 {trades.length} 条）
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn" disabled={tradesPage <= 1} onClick={() => setTradesPage((p) => Math.max(1, p - 1))}>
                  上一页
                </button>
                <button
                  className="btn"
                  disabled={tradesPage >= totalTradePages}
                  onClick={() => setTradesPage((p) => Math.min(totalTradePages, p + 1))}
                >
                  下一页
                </button>
              </div>
            </div>
          </>
        )}

        {trades && trades.length === 0 && (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>当前选择暂无成交记录。</div>
        )}

        {trades === null && dataLoading && <LoadingSpinner />}
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
            <div className="label" style={{ marginBottom: 12 }}>启动回测</div>
            <div style={{ display: 'grid', gap: 12 }}>
              <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                开始日期
                <input
                  type="date"
                  value={backtestStartDate}
                  onChange={(e) => setBacktestStartDate(e.target.value)}
                  style={{ width: '100%', marginTop: 6 }}
                />
              </label>
              <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                结束日期
                <input
                  type="date"
                  value={backtestEndDate}
                  onChange={(e) => setBacktestEndDate(e.target.value)}
                  style={{ width: '100%', marginTop: 6 }}
                />
              </label>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <button className="btn" onClick={() => setShowBacktestConfig(false)} disabled={runningBacktest}>
                取消
              </button>
              <button
                className="btn btn-primary"
                onClick={() => handleRunBacktest(backtestStartDate, backtestEndDate)}
                disabled={runningBacktest}
              >
                {runningBacktest ? '回测中...' : '确认'}
              </button>
            </div>
          </div>
        </div>
      )}

      <StrategyManager traderId={trader.id} onUpdate={() => api.getTrader(trader.id).then(setTrader)} />

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
