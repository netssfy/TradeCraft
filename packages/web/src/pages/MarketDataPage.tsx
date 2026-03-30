import { useEffect, useMemo, useState } from 'react';
import type { MarketDataAvailability } from '@tradecraft/shared/types';
import ErrorMessage from '../components/ErrorMessage';
import LoadingSpinner from '../components/LoadingSpinner';
import { useI18n } from '../hooks/useI18n';
import { api } from '../services/api';

function uniqueCount(values: string[]): number {
  return new Set(values).size;
}

export default function MarketDataPage() {
  const { tx } = useI18n();
  const [data, setData] = useState<MarketDataAvailability | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.listMarketDataAvailability();
        if (!cancelled) setData(res);
      } catch (e: any) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => {
    const items = data?.items ?? [];
    return {
      markets: uniqueCount(items.map((item) => item.market)),
      symbols: uniqueCount(items.map((item) => `${item.market}:${item.symbol}`)),
      intervals: uniqueCount(items.map((item) => item.interval)),
      combinations: items.length,
      files: data?.total_files ?? 0,
    };
  }, [data]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={`${tx('加载失败', 'Load failed')}: ${error}`} />;

  const items = data?.items ?? [];

  const toggleExpanded = (key: string) => {
    setExpandedKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (items.length === 0) {
    return (
      <div className="empty-state">
        <h3>{tx('暂无市场数据', 'No market data yet')}</h3>
        <p>{tx('请先在后台下载或写入 data/market 数据。', 'Please download or write data into data/market first.')}</p>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600 }}>{tx('市场数据可用性', 'Market Data Availability')}</h1>
        <div style={{ color: 'var(--text-muted)', marginTop: 6 }}>
          {tx('数据根目录', 'Data root')}: <span className="mono">{data?.root}</span>
        </div>
      </div>

      <div className="market-stats-grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="market-stat-label">{tx('市场数', 'Markets')}</div>
          <div className="market-stat-value mono">{stats.markets}</div>
        </div>
        <div className="card">
          <div className="market-stat-label">{tx('标的数', 'Symbols')}</div>
          <div className="market-stat-value mono">{stats.symbols}</div>
        </div>
        <div className="card">
          <div className="market-stat-label">{tx('周期数', 'Intervals')}</div>
          <div className="market-stat-value mono">{stats.intervals}</div>
        </div>
        <div className="card">
          <div className="market-stat-label">{tx('组合数', 'Combinations')}</div>
          <div className="market-stat-value mono">{stats.combinations}</div>
        </div>
        <div className="card">
          <div className="market-stat-label">{tx('文件总数', 'Total files')}</div>
          <div className="market-stat-value mono">{stats.files}</div>
        </div>
      </div>

      <div className="trader-table">
        <div className="market-table-head">
          <div>{tx('市场', 'Market')}</div>
          <div>{tx('标的', 'Symbol')}</div>
          <div>{tx('周期', 'Interval')}</div>
          <div>{tx('文件数', 'Files')}</div>
          <div>{tx('范围', 'Range')}</div>
          <div>{tx('月份列表', 'Periods')}</div>
        </div>
        {items.map((item) => (
          <div key={`${item.market}-${item.symbol}-${item.interval}`} className="market-row">
            <div className="mono">{item.market}</div>
            <div className="mono">{item.symbol}</div>
            <div className="mono">{item.interval}</div>
            <div className="mono">{item.file_count}</div>
            <div className="mono">
              {item.start_period && item.end_period ? `${item.start_period} ~ ${item.end_period}` : 'N/A'}
            </div>
            <div className="market-periods mono">
              <div
                className={`market-period-links ${expandedKeys[`${item.market}-${item.symbol}-${item.interval}`] ? '' : 'market-period-links--collapsed'}`}
              >
                {item.periods.map((period) => (
                  <a
                    key={period}
                    href={`/market-data/file/${encodeURIComponent(item.market)}/${encodeURIComponent(item.symbol)}/${encodeURIComponent(item.interval)}/${encodeURIComponent(period)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="market-period-link"
                  >
                    {period}
                  </a>
                ))}
              </div>
              {item.periods.length > 12 && (
                <button
                  type="button"
                  className="market-period-toggle"
                  onClick={() => toggleExpanded(`${item.market}-${item.symbol}-${item.interval}`)}
                >
                  {expandedKeys[`${item.market}-${item.symbol}-${item.interval}`]
                    ? tx('收起', 'Collapse')
                    : tx('展开全部', 'Show all')}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
