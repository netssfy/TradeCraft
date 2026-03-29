import { useEffect, useRef, useState } from 'react';
import type { StrategyFile } from '@tradecraft/shared/types';
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
  const nextMessageIdRef = useRef(1);

  const [strategies, setStrategies] = useState<StrategyFile[]>([]);
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
      .then(setStrategies)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [traderId]);

  const handleSetActive = async (filename: string) => {
    try {
      await api.setActiveStrategy(traderId, filename);
      appendMessage('result', `Strategy activated: ${filename}`);
      load();
      onUpdate();
    } catch (e: any) {
      appendMessage('error', e.message);
      setError(e.message);
    }
  };

  const handleResearch = async () => {
    setResearching(true);
    setMessages([]);
    setError(null);

    try {
      await researchStrategySSE(traderId, {
        onLog: (msg) => appendLogLine(msg),
        onResult: (data) => {
          const list = data.strategies.length ? data.strategies.join(', ') : '(none)';
          appendMessage('result', `Research completed. Generated strategies: ${list}`);
          load();
          onUpdate();
          setResearching(false);
        },
        onError: (msg) => {
          appendMessage('error', msg);
          setError(msg);
          setResearching(false);
        },
      });
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
        <div className="label" style={{ margin: 0 }}>Strategy Files</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={handleResearch} disabled={researching}>
            {researching ? 'Researching...' : 'AI Research'}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {strategies.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>No strategy files yet.</div>
      ) : (
        <div>
          {strategies.map((s) => (
            <div
              key={s.filename}
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="mono" style={{ fontSize: 13 }}>{s.filename}</span>
                {s.is_active && <span className="badge badge-green">Active</span>}
              </div>
              {!s.is_active && (
                <button className="btn" onClick={() => handleSetActive(s.filename)} style={{ padding: '4px 8px', fontSize: 12 }}>
                  Set Active
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <StreamMessagePanel title="Research Stream Messages" messages={messages} />
    </div>
  );
}
