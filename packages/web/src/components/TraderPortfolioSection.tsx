import type { Portfolio } from '@tradecraft/shared/types';
import { useI18n } from '../hooks/useI18n';
import LoadingSpinner from './LoadingSpinner';
import PortfolioChart from './PortfolioChart';

type Mode = 'paper' | 'backtest';

interface TraderPortfolioSectionProps {
  mode: Mode;
  selectedBacktestRunId: string | null;
  dataLoading: boolean;
  portfolioError: string | null;
  portfolio: Portfolio | null;
  initialCash: number;
}

export default function TraderPortfolioSection({
  mode,
  selectedBacktestRunId,
  dataLoading,
  portfolioError,
  portfolio,
  initialCash,
}: TraderPortfolioSectionProps) {
  const { tx } = useI18n();

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>
        {tx('收益曲线', 'Return Curve')} ({mode === 'paper' ? tx('模拟盘', 'Paper') : `${tx('回测', 'Backtest')} ${selectedBacktestRunId || ''}`})
      </div>
      {dataLoading ? (
        <LoadingSpinner />
      ) : portfolioError ? (
        <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>{portfolioError}</div>
      ) : portfolio ? (
        <PortfolioChart portfolio={portfolio} initialCash={initialCash} />
      ) : (
        <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>{tx('暂无数据。', 'No data.')}</div>
      )}
    </div>
  );
}
