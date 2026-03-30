import type { BacktestReport } from '@tradecraft/shared/types';
import { useI18n } from '../hooks/useI18n';

type Mode = 'paper' | 'backtest';

interface TraderDataScopeSectionProps {
  mode: Mode;
  backtestRuns: string[];
  backtestRunReports: Record<string, BacktestReport | null>;
  backtestStrategyOptions: string[];
  selectedBacktestStrategyFilename: string | null;
  selectedBacktestRunId: string | null;
  selectedPaperRunId: string | null;
  onModeChange: (mode: Mode) => void;
  onBacktestStrategyChange: (filename: string | null) => void;
  onBacktestRunChange: (runId: string) => void;
}

export default function TraderDataScopeSection({
  mode,
  backtestRuns,
  backtestRunReports,
  backtestStrategyOptions,
  selectedBacktestStrategyFilename,
  selectedBacktestRunId,
  selectedPaperRunId,
  onModeChange,
  onBacktestStrategyChange,
  onBacktestRunChange,
}: TraderDataScopeSectionProps) {
  const { tx } = useI18n();

  const shortDate = (value: string | undefined) => (value ? value.split('T')[0] || value : '');

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <div className="label" style={{ margin: 0 }}>
          {tx('数据范围', 'Data Scope')}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            className={`btn ${mode === 'paper' ? 'btn-primary' : ''}`}
            onClick={() => onModeChange('paper')}
            style={{ padding: '4px 12px', fontSize: 12 }}
          >
            {tx('模拟盘', 'Paper')}
          </button>
          <button
            className={`btn ${mode === 'backtest' ? 'btn-primary' : ''}`}
            onClick={() => onModeChange('backtest')}
            style={{ padding: '4px 12px', fontSize: 12 }}
          >
            {tx('回测', 'Backtest')}
          </button>
        </div>
      </div>

      {mode === 'backtest' && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>{tx('回测策略', 'Backtest Strategy')}</div>
          <select
            value={selectedBacktestStrategyFilename ?? '__ALL__'}
            onChange={(e) => onBacktestStrategyChange(e.target.value === '__ALL__' ? null : e.target.value)}
            style={{ width: '100%', marginBottom: 10 }}
          >
            <option value="__ALL__">{tx('全部策略', 'All strategies')}</option>
            {backtestStrategyOptions.map((filename) => (
              <option key={filename} value={filename}>
                {filename}
              </option>
            ))}
          </select>

          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>{tx('回测 Run ID', 'Backtest Run ID')}</div>
          {backtestRuns.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {backtestRuns.map((runId) => {
                const report = backtestRunReports[runId];
                const rangeText =
                  report && report.backtest_start && report.backtest_end
                    ? `${shortDate(report.backtest_start)} ~ ${shortDate(report.backtest_end)}`
                    : null;

                return (
                  <button
                    key={runId}
                    className={`btn ${selectedBacktestRunId === runId ? 'btn-primary' : ''}`}
                    onClick={() => onBacktestRunChange(runId)}
                    style={{ padding: '4px 8px', fontSize: 12 }}
                    title={rangeText ? `${runId} (${rangeText})` : runId}
                  >
                    {runId}
                  </button>
                );
              })}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              {selectedBacktestStrategyFilename
                ? tx('该策略暂无回测运行记录。', 'No backtest runs for selected strategy.')
                : tx('暂无回测运行记录。', 'No backtest runs yet.')}
            </div>
          )}
        </div>
      )}

      {mode === 'paper' && (
        <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>
          {tx('当前模拟盘运行', 'Current paper run')}: {selectedPaperRunId || tx('（无）', '(none)')}
        </div>
      )}
    </div>
  );
}
