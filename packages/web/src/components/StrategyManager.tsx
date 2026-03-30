import { useEffect, useRef, useState } from 'react';
import type { StrategyFile } from '@tradecraft/shared/types';
import { Link } from 'react-router-dom';
import { useI18n } from '../hooks/useI18n';
import { api, researchStrategySSE } from '../services/api';
import LoadingSpinner from './LoadingSpinner';
import StreamMessagePanel, { type StreamMessage, type StreamMessageType } from './StreamMessagePanel';

interface StrategyManagerProps {
  traderId: string;
  onUpdate: () => void;
}

function inferMessageType(message: string): StreamMessageType {
  const text = message.toLowerCase();
  if (text.includes('error') || text.includes('failed') || text.includes('exception') || text.includes('traceback')) {
    return 'error';
  }
  if (text.includes('warn') || text.includes('warning')) {
    return 'warning';
  }
  if (text.includes('result') || text.includes('success') || text.includes('completed') || text.includes('done')) {
    return 'result';
  }
  return 'info';
}

export default function StrategyManager({ traderId, onUpdate }: StrategyManagerProps) {
  const { tx } = useI18n();
  const nextMessageIdRef = useRef(1);

  const [strategies, setStrategies] = useState<StrategyFile[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [researching, setResearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<StreamMessage[]>([]);

  const appendMessage = (type: StreamMessageType, text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: nextMessageIdRef.current++,
        type,
        text,
      },
    ]);
  };

  const appendLogLine = (text: string) => {
    const type = inferMessageType(text);
    if (type !== 'info') {
      appendMessage(type, text);
      return;
    }

    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.type === 'info' && last.text.length < 4000) {
        return [
          ...prev.slice(0, -1),
          {
            ...last,
            text: `${last.text}\n${text}`,
          },
        ];
      }
      return [
        ...prev,
        {
          id: nextMessageIdRef.current++,
          type: 'info',
          text,
        },
      ];
    });
  };

  const load = () => {
    setLoading(true);
    api
      .listStrategies(traderId)
      .then((list) => {
        setStrategies(list);
        const active = list.find((item) => item.is_active)?.filename ?? null;
        setSelectedStrategy((prev) => {
          if (prev && list.some((item) => item.filename === prev)) return prev;
          return active ?? list[0]?.filename ?? null;
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [traderId]);

  const handleSetActive = async (filename: string) => {
    try {
      await api.setActiveStrategy(traderId, filename);
      appendMessage('result', `${tx('已激活策略', 'Strategy activated')}: ${filename}`);
      load();
      onUpdate();
    } catch (e: any) {
      appendMessage('error', e.message);
      setError(e.message);
    }
  };

  const handleResearch = async (mode: 'create' | 'update') => {
    if (mode === 'update' && !selectedStrategy) {
      setError(tx('请先选择策略。', 'Please select a strategy first.'));
      return;
    }

    setResearching(true);
    setMessages([]);
    setError(null);

    try {
      await researchStrategySSE(
        traderId,
        {
          onLog: (msg) => appendLogLine(msg),
          onResult: (data) => {
            const list = data.strategies.length ? data.strategies.join(', ') : tx('（无）', '(none)');
            appendMessage('result', `${tx('研究完成，生成策略', 'Research completed. Generated strategies')}: ${list}`);
            load();
            onUpdate();
            setResearching(false);
            window.location.reload();
          },
          onError: (msg) => {
            appendMessage('error', msg);
            setError(msg);
            setResearching(false);
          },
        },
        {
          mode,
          target: mode === 'update' ? selectedStrategy ?? undefined : undefined,
        }
      );
    } catch (e: any) {
      appendMessage('error', e.message);
      setError(e.message);
      setResearching(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="label" style={{ margin: 0 }}>{tx('策略文件', 'Strategy Files')}</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={() => handleResearch('create')} disabled={researching}>
            {researching ? tx('研究中...', 'Researching...') : tx('新建策略', 'Create New Strategy')}
          </button>
          <button className="btn" onClick={() => handleResearch('update')} disabled={researching || !selectedStrategy}>
            {researching ? tx('研究中...', 'Researching...') : tx('更新已选策略', 'Update Selected Strategy')}
          </button>
        </div>
      </div>

      {error && <div className="error-message" style={{ marginBottom: 12 }}>{error}</div>}

      {strategies.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>{tx('暂无策略文件。', 'No strategy files yet.')}</div>
      ) : (
        <div>
          {strategies.map((s) => (
            <div
              key={s.filename}
              onClick={() => setSelectedStrategy(s.filename)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 0',
                borderBottom: '1px solid var(--border-color)',
                cursor: 'pointer',
                background: selectedStrategy === s.filename ? 'rgba(30, 64, 175, 0.08)' : 'transparent',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Link
                  className="mono"
                  to={`/traders/${traderId}/strategy/${encodeURIComponent(s.filename)}`}
                  onClick={(e) => e.stopPropagation()}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: 13, color: 'var(--text-primary)', textDecoration: 'underline' }}
                >
                  {s.filename}
                </Link>
                {s.is_active && <span className="badge badge-green">{tx('激活中', 'Active')}</span>}
                {selectedStrategy === s.filename && <span className="badge">{tx('已选择', 'Selected')}</span>}
              </div>
              {!s.is_active && (
                <button className="btn" onClick={() => handleSetActive(s.filename)} style={{ padding: '4px 8px', fontSize: 12 }}>
                  {tx('设为激活', 'Set Active')}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <StreamMessagePanel title={tx('研究流消息', 'Research Stream Messages')} messages={messages} />
    </div>
  );
}
