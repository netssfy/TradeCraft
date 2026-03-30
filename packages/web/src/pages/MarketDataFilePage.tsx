import { Link, useParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import type { MarketDataFileDetail } from '@tradecraft/shared/types';
import ErrorMessage from '../components/ErrorMessage';
import LoadingSpinner from '../components/LoadingSpinner';
import { useI18n } from '../hooks/useI18n';
import { api } from '../services/api';

const PAGE_SIZE = 50;

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') {
    if (Number.isFinite(value)) return value.toString();
    return 'NaN';
  }
  return String(value);
}

export default function MarketDataFilePage() {
  const { tx } = useI18n();
  const params = useParams<{ market: string; symbol: string; interval: string; period: string }>();
  const market = params.market ?? '';
  const symbol = params.symbol ?? '';
  const interval = params.interval ?? '';
  const period = params.period ?? '';

  const [data, setData] = useState<MarketDataFileDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [market, symbol, interval, period]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getMarketDataFile(market, symbol, interval, period, page, PAGE_SIZE);
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
  }, [market, symbol, interval, period, page]);

  const totalPages = useMemo(() => {
    if (!data) return 1;
    return Math.max(1, Math.ceil(data.total_rows / data.page_size));
  }, [data]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={`${tx('加载失败', 'Load failed')}: ${error}`} />;
  if (!data) return <ErrorMessage message={tx('未找到文件数据', 'File data not found')} />;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link to="/market-data" className="btn">
          {tx('返回市场数据列表', 'Back to market data')}
        </Link>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, marginBottom: 10 }}>
          {tx('文件明细', 'File Detail')} <span className="mono">{`${data.market}/${data.symbol}/${data.interval}/${data.period}`}</span>
        </h1>
        <div className="market-file-meta">
          <div>
            {tx('文件路径', 'File path')}: <span className="mono">{data.path}</span>
          </div>
          <div>
            {tx('总行数', 'Total rows')}: <span className="mono">{data.total_rows}</span>
          </div>
          <div>
            {tx('当前分页', 'Current page')}: <span className="mono">{`${data.page} / ${totalPages}`}</span>
          </div>
        </div>
      </div>

      <div className="market-file-pagination" style={{ marginBottom: 12 }}>
        <button className="btn" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
          {tx('上一页', 'Previous')}
        </button>
        <button className="btn" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
          {tx('下一页', 'Next')}
        </button>
      </div>

      <div className="market-file-table-wrap">
        <table className="market-file-table">
          <thead>
            <tr>
              {data.columns.map((column) => (
                <th key={column} className="mono">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.length === 0 ? (
              <tr>
                <td colSpan={Math.max(1, data.columns.length)}>{tx('该分页暂无数据', 'No rows in this page')}</td>
              </tr>
            ) : (
              data.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {data.columns.map((column) => (
                    <td key={column} className="mono">
                      {formatCellValue(row[column])}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
