import type { Trade } from '@tradecraft/shared/types';
import { formatCurrency } from '@tradecraft/shared/utils';
import { useI18n } from '../hooks/useI18n';
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
  const { tx } = useI18n();

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>
        {tx('成交记录', 'Trades')}
      </div>

      {trades && trades.length > 0 && (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)' }}>{tx('时间', 'Time')}</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)' }}>{tx('标的', 'Symbol')}</th>
                  <th style={{ textAlign: 'center', padding: '8px 12px', color: 'var(--text-muted)' }}>{tx('方向', 'Side')}</th>
                  <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)' }}>{tx('数量', 'Qty')}</th>
                  <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)' }}>{tx('价格', 'Price')}</th>
                  <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)' }}>{tx('手续费', 'Commission')}</th>
                </tr>
              </thead>
              <tbody>
                {pagedTrades.map((trade, i) => (
                  <tr key={`${trade.timestamp}-${trade.symbol}-${i}`} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td className="mono" style={{ padding: '8px 12px' }}>{trade.timestamp}</td>
                    <td style={{ padding: '8px 12px' }}>{trade.symbol}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                      <span className={`badge ${trade.direction === 'buy' ? 'badge-green' : 'badge-red'}`}>
                        {trade.direction === 'buy' ? tx('买入', 'Buy') : tx('卖出', 'Sell')}
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
              {tx('第', 'Page')} {tradesPage} / {totalTradePages} {tx('页（共', 'of')} {trades.length} {tx('条）', 'items)')}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn" disabled={tradesPage <= 1} onClick={onPrevPage}>{tx('上一页', 'Prev')}</button>
              <button className="btn" disabled={tradesPage >= totalTradePages} onClick={onNextPage}>{tx('下一页', 'Next')}</button>
            </div>
          </div>
        </>
      )}

      {trades && trades.length === 0 && <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>{tx('当前选择暂无成交记录。', 'No trades for current selection.')}</div>}

      {trades === null && dataLoading && <LoadingSpinner />}
    </div>
  );
}
