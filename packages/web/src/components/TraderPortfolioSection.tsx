import type { Portfolio } from '@tradecraft/shared/types';
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
  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>
        收益曲线 ({mode === 'paper' ? '模拟盘' : `回测 ${selectedBacktestRunId || ''}`})
      </div>
      {dataLoading ? (
        <LoadingSpinner />
      ) : portfolioError ? (
        <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>{portfolioError}</div>
      ) : portfolio ? (
        <PortfolioChart portfolio={portfolio} initialCash={initialCash} />
      ) : (
        <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>暂无数据。</div>
      )}
    </div>
  );
}
