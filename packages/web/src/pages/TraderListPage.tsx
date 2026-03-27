import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Trader } from '@tradecraft/shared/types';
import { api } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { formatCurrency } from '@tradecraft/shared/utils';

export default function TraderListPage() {
  const [traders, setTraders] = useState<Trader[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTraders()
      .then(setTraders)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={`加载失败: ${error}`} />;

  if (traders.length === 0) {
    return (
      <div className="empty-state">
        <h3>暂无交易员</h3>
        <p style={{ marginBottom: 16 }}>创建你的第一个 AI 交易员开始观测</p>
        <Link to="/traders/create" className="btn btn-primary">
          创建交易员
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600 }}>交易员列表</h1>
        <Link to="/traders/create" className="btn btn-primary">
          + 创建交易员
        </Link>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
        {traders.map((trader) => (
          <Link
            key={trader.id}
            to={`/traders/${trader.id}`}
            className="card"
            style={{ display: 'block', transition: 'border-color 0.15s' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <h3 style={{ fontSize: 18, fontWeight: 600 }}>{trader.id}</h3>
              <span className="badge badge-yellow">{trader.market}</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>初始资金</span>
                <div className="mono" style={{ fontWeight: 500 }}>
                  ¥{formatCurrency(trader.initial_cash)}
                </div>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>激活策略</span>
                <div style={{ fontWeight: 500 }}>
                  {trader.active_strategy || '未设置'}
                </div>
              </div>
            </div>
            <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {trader.allowed_symbols.map((s) => (
                <span
                  key={s}
                  style={{
                    padding: '2px 6px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 4,
                    fontSize: 12,
                    color: 'var(--text-secondary)',
                  }}
                >
                  {s}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
