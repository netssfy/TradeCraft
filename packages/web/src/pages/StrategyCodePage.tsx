import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { StrategyCode } from '@tradecraft/shared/types';
import ErrorMessage from '../components/ErrorMessage';
import LoadingSpinner from '../components/LoadingSpinner';
import { useI18n } from '../hooks/useI18n';
import { api } from '../services/api';

export default function StrategyCodePage() {
  const { tx } = useI18n();
  const { id, filename } = useParams<{ id: string; filename: string }>();

  const decodedFilename = useMemo(() => {
    if (!filename) return '';
    try {
      return decodeURIComponent(filename);
    } catch {
      return filename;
    }
  }, [filename]);

  const [strategyCode, setStrategyCode] = useState<StrategyCode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id || !decodedFilename) return;

    setLoading(true);
    setError(null);
    api
      .getStrategyCode(id, decodedFilename)
      .then((data) => setStrategyCode(data))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, decodedFilename]);

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div>
        <ErrorMessage message={error} />
        {id && (
          <Link to={`/traders/${id}`} className="btn" style={{ marginTop: 16 }}>
            {tx('返回交易员详情', 'Back to trader detail')}
          </Link>
        )}
      </div>
    );
  }

  if (!strategyCode || !id) return null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Link to={`/traders/${id}`} style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            {tx('返回交易员详情', 'Back to trader detail')}
          </Link>
          <h1 style={{ fontSize: 24, fontWeight: 600, marginTop: 8 }}>
            {tx('策略代码', 'Strategy Code')}: <span className="mono">{strategyCode.filename}</span>
          </h1>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <pre
          style={{
            margin: 0,
            padding: 16,
            overflowX: 'auto',
            fontSize: 13,
            lineHeight: 1.6,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
          }}
        >
          <code>{strategyCode.code}</code>
        </pre>
      </div>
    </div>
  );
}
