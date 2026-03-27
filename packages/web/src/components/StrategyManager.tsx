import { useEffect, useState, useRef } from 'react';
import type { StrategyFile } from '@tradecraft/shared/types';
import { api, researchStrategySSE } from '../services/api';
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
  const [researching, setResearching] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

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

  const handleResearch = async () => {
    setResearching(true);
    setLogs([]);
    setError(null);
    try {
      await researchStrategySSE(traderId, {
        onLog: (msg) => {
          setLogs((prev) => [...prev, msg]);
          setTimeout(() => logsEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
        },
        onResult: () => {
          load();
          onUpdate();
          setResearching(false);
        },
        onError: (msg) => {
          setError(msg);
          setResearching(false);
        },
      });
    } catch (e: any) {
      setError(e.message);
      setResearching(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="label" style={{ margin: 0 }}>策略文件</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-primary"
            onClick={handleResearch}
            disabled={researching || uploading}
          >
            {researching ? '研究中...' : 'AI 研究策略'}
          </button>
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
            disabled={uploading || researching}
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

      {logs.length > 0 && (
        <div style={{ marginTop: 16, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
          <div className="label" style={{ marginBottom: 8 }}>AI 研究日志</div>
          <div
            style={{
              maxHeight: 300,
              overflow: 'auto',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              lineHeight: 1.6,
              color: 'var(--text-secondary)',
              background: 'var(--bg-primary)',
              borderRadius: 8,
              padding: 12,
            }}
          >
            {logs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}
    </div>
  );
}
