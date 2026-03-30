import type { Trade } from '@tradecraft/shared/types';
import { formatCurrency } from '@tradecraft/shared/utils';
import LoadingSpinner from './LoadingSpinner';

interface TraderTradesSectionProps {
  trades: Trade[] | null;
  pagedTrades: Trade[];
  tradesPage: number;
  totalTradePages: number;
  dataLoading: boolean;
  onPrevPage: () => void;
  onNextPage: () => void;
}

export default function TraderTradesSection({
  trades,
  pagedTrades,
  tradesPage,
  totalTradePages,
  dataLoading,
  onPrevPage,
  onNextPage,
}: TraderTradesSectionProps) {
  return (
    <div className="card">
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
                    <td className="mono" style={{ padding: '8px 12px' }}>
                      {trade.timestamp}
                    </td>
                    <td style={{ padding: '8px 12px' }}>{trade.symbol}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                      <span className={`badge ${trade.direction === 'buy' ? 'badge-green' : 'badge-red'}`}>
                        {trade.direction === 'buy' ? '买入' : '卖出'}
                      </span>
                    </td>
                    <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>
                      {trade.quantity}
                    </td>
                    <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>
                      {formatCurrency(trade.price)}
                    </td>
                    <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>
                      {formatCurrency(trade.commission)}
                    </td>
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
              <button className="btn" disabled={tradesPage <= 1} onClick={onPrevPage}>
                上一页
              </button>
              <button className="btn" disabled={tradesPage >= totalTradePages} onClick={onNextPage}>
                下一页
              </button>
            </div>
          </div>
        </>
      )}

      {trades && trades.length === 0 && <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>当前选择暂无成交记录。</div>}

      {trades === null && dataLoading && <LoadingSpinner />}
    </div>
  );
}
