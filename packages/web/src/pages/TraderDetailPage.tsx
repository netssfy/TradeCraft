import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import type { Trader, Portfolio, Trade, TradeRuns } from '@tradecraft/shared/types';
import { TRAIT_LABELS, formatCurrency } from '@tradecraft/shared/utils';
import { api } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import PortfolioChart from '../components/PortfolioChart';
import StrategyManager from '../components/StrategyManager';
import EditTraderModal from '../components/EditTraderModal';

export default function TraderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [trader, setTrader] = useState<Trader | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [tradeRuns, setTradeRuns] = useState<TradeRuns | null>(null);
  const [selectedRun, setSelectedRun] = useState<{ mode: string; runId: string } | null>(null);
  const [trades, setTrades] = useState<Trade[] | null>(null);
  const [mode, setMode] = useState<'paper' | 'backtest'>('paper');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [showEdit, setShowEdit] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    Promise.all([
      api.getTrader(id),
      api.listTradeRuns(id),
    ])
      .then(([t, runs]) => {
        setTrader(t);
        setTradeRuns(runs);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    setPortfolioError(null);
    setPortfolio(null);
    api
      .getPortfolio(id, mode)
      .then(setPortfolio)
      .catch((e) => {
        if (e.message.includes('404')) {
          setPortfolioError('该模式暂无持仓数据');
        } else {
          setPortfolioError(e.message);
        }
      });
  }, [id, mode]);

  const loadTrades = async (m: string, runId: string) => {
    if (!id) return;
    setSelectedRun({ mode: m, runId });
    setTrades(null);
    try {
      const t = await api.getTrades(id, m, runId);
      setTrades(t);
    } catch (e: any) {
      setTrades([]);
    }
  };

  const handleDelete = async () => {
    if (!id || !window.confirm('确定要删除该交易员吗？此操作不可撤销。')) return;
    setDeleting(true);
    try {
      await api.deleteTrader(id);
      navigate('/');
    } catch (e: any) {
      setError(`删除失败: ${e.message}`);
      setDeleting(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return (
    <div>
      <ErrorMessage message={error} />
      <Link to="/" className="btn" style={{ marginTop: 16 }}>返回列表</Link>
    </div>
  );
  if (!trader) return null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Link to="/" style={{ color: 'var(--text-muted)', fontSize: 13 }}>← 返回列表</Link>
          <h1 style={{ fontSize: 24, fontWeight: 600, marginTop: 8 }}>{trader.id}</h1>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" onClick={() => setShowEdit(true)}>编辑</button>
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
              <div><span className="badge badge-yellow">{trader.market}</span></div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>初始资金</span>
              <div className="mono">¥{formatCurrency(trader.initial_cash)}</div>
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
                <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                  {TRAIT_LABELS[key] || key}
                </span>
                <span style={{ fontSize: 13 }}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div className="label" style={{ margin: 0 }}>收益率曲线</div>
          <div style={{ display: 'flex', gap: 4 }}>
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
        {portfolioError ? (
          <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>{portfolioError}</div>
        ) : portfolio ? (
          <PortfolioChart portfolio={portfolio} initialCash={trader.initial_cash} />
        ) : (
          <LoadingSpinner />
        )}
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="label" style={{ marginBottom: 12 }}>持仓快照</div>
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
                    <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>
                      ¥{formatCurrency(snap.cash)}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      {Object.entries(snap.positions).map(([sym, pos]) => (
                        <span key={sym} style={{ marginRight: 12 }}>
                          {sym}: <span className="mono">{pos.quantity}</span>股 @<span className="mono">¥{formatCurrency(pos.avg_cost)}</span>
                        </span>
                      ))}
                      {Object.keys(snap.positions).length === 0 && <span style={{ color: 'var(--text-muted)' }}>空仓</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
            {portfolioError || '暂无持仓数据'}
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="label" style={{ marginBottom: 12 }}>成交记录</div>
        {tradeRuns && (tradeRuns.paper.length > 0 || tradeRuns.backtest.length > 0) ? (
          <div>
            <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
              {tradeRuns.paper.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>模拟盘</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {tradeRuns.paper.map((runId) => (
                      <button
                        key={runId}
                        className={`btn ${selectedRun?.mode === 'paper' && selectedRun?.runId === runId ? 'btn-primary' : ''}`}
                        onClick={() => loadTrades('paper', runId)}
                        style={{ padding: '4px 8px', fontSize: 12 }}
                      >
                        {runId}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {tradeRuns.backtest.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>回测</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {tradeRuns.backtest.map((runId) => (
                      <button
                        key={runId}
                        className={`btn ${selectedRun?.mode === 'backtest' && selectedRun?.runId === runId ? 'btn-primary' : ''}`}
                        onClick={() => loadTrades('backtest', runId)}
                        style={{ padding: '4px 8px', fontSize: 12 }}
                      >
                        {runId}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {trades && trades.length > 0 && (
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
                    {trades.map((trade, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td className="mono" style={{ padding: '8px 12px' }}>{trade.timestamp}</td>
                        <td style={{ padding: '8px 12px' }}>{trade.symbol}</td>
                        <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                          <span className={`badge ${trade.direction === 'buy' ? 'badge-green' : 'badge-red'}`}>
                            {trade.direction === 'buy' ? '买入' : '卖出'}
                          </span>
                        </td>
                        <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>{trade.quantity}</td>
                        <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>¥{formatCurrency(trade.price)}</td>
                        <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>¥{formatCurrency(trade.commission)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {trades && trades.length === 0 && (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>该运行无成交记录</div>
            )}
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>暂无成交记录</div>
        )}
      </div>

      <StrategyManager traderId={trader.id} onUpdate={() => {
        api.getTrader(trader.id).then(setTrader);
      }} />

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
