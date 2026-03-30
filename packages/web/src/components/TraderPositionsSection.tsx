import type { Portfolio } from '@tradecraft/shared/types';
import { formatCurrency } from '@tradecraft/shared/utils';
import { useI18n } from '../hooks/useI18n';

interface TraderPositionsSectionProps {
  portfolio: Portfolio | null;
  portfolioError: string | null;
}

export default function TraderPositionsSection({ portfolio, portfolioError }: TraderPositionsSectionProps) {
  const { tx } = useI18n();

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>
        {tx('持仓快照', 'Position Snapshot')}
      </div>
      {portfolio && portfolio.snapshots.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)' }}>{tx('日期', 'Date')}</th>
                <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)' }}>{tx('现金', 'Cash')}</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)' }}>{tx('持仓', 'Positions')}</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.snapshots
                .slice()
                .reverse()
                .map((snap) => (
                  <tr key={snap.date} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td className="mono" style={{ padding: '8px 12px' }}>
                      {snap.date}
                    </td>
                    <td className="mono" style={{ padding: '8px 12px', textAlign: 'right' }}>
                      {formatCurrency(snap.cash)}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      {Object.entries(snap.positions).map(([sym, pos]) => (
                        <span key={sym} style={{ marginRight: 12 }}>
                          {sym}: <span className="mono">{pos.quantity}</span> @ <span className="mono">{formatCurrency(pos.avg_cost)}</span>
                        </span>
                      ))}
                      {Object.keys(snap.positions).length === 0 && <span style={{ color: 'var(--text-muted)' }}>{tx('空仓', 'No positions')}</span>}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>{portfolioError || tx('暂无持仓数据。', 'No position data.')}</div>
      )}
    </div>
  );
}
