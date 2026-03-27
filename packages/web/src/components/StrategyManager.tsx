import { useEffect, useState, useRef } from 'react';
import type { StrategyFile } from '@tradecraft/shared/types';
import { api } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

interface StrategyManagerProps {
  traderId: string;
  onUpdate: () => void;
}

export default function StrategyManager({ traderId, onUpdate }: StrategyManagerProps) {
  const [strategies, setStrategies] = useState<StrategyFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = () => {
    setLoading(true);
    api
      .listStrategies(traderId)
      .then(setStrategies)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [traderId]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.py')) {
      setError('仅支持 .py 文件');
      if (fileRef.current) fileRef.current.value = '';
      return;
    }

    setUploading(true);
    setError(null);
    try {
      await api.uploadStrategy(traderId, file);
      load();
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleSetActive = async (filename: string) => {
    try {
      await api.setActiveStrategy(traderId, filename);
      load();
      onUpdate();
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="label" style={{ margin: 0 }}>策略文件</div>
        <div>
          <input
            ref={fileRef}
            type="file"
            accept=".py"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <button
            className="btn"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? '上传中...' : '上传策略'}
          </button>
        </div>
      </div>

      {error && <div className="error-message" style={{ marginBottom: 12 }}>{error}</div>}

      {strategies.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
          暂无策略文件
        </div>
      ) : (
        <div>
          {strategies.map((s) => (
            <div
              key={s.filename}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 0',
                borderBottom: '1px solid var(--border-color)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="mono" style={{ fontSize: 13 }}>{s.filename}</span>
                {s.is_active && <span className="badge badge-green">激活</span>}
              </div>
              {!s.is_active && (
                <button
                  className="btn"
                  onClick={() => handleSetActive(s.filename)}
                  style={{ padding: '4px 8px', fontSize: 12 }}
                >
                  设为激活
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
