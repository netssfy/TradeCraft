import { useI18n } from '../hooks/useI18n';

export type StreamMessageType = 'info' | 'warning' | 'error' | 'result';

export interface StreamMessage {
  id: number;
  type: StreamMessageType;
  text: string;
}

interface StreamMessagePanelProps {
  title: string;
  messages: StreamMessage[];
  maxHeight?: number;
}

const TYPE_BADGE_CLASS: Record<StreamMessageType, string> = {
  error: 'badge badge-red',
  result: 'badge badge-green',
  warning: 'badge badge-yellow',
  info: 'badge',
};

const TYPE_ORDER: StreamMessageType[] = ['error', 'result', 'warning', 'info'];
const COLLAPSE_LIMIT = 240;

function renderMessageBody(text: string, expandLabel: string) {
  if (text.length <= COLLAPSE_LIMIT) {
    return <div style={{ whiteSpace: 'pre-wrap' }}>{text}</div>;
  }

  return (
    <details>
      <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}>
        {text.slice(0, 120)}... ({expandLabel})
      </summary>
      <div style={{ whiteSpace: 'pre-wrap', marginTop: 8 }}>{text}</div>
    </details>
  );
}

export default function StreamMessagePanel({ title, messages, maxHeight = 320 }: StreamMessagePanelProps) {
  const { tx } = useI18n();

  if (messages.length === 0) return null;

  const typeLabel: Record<StreamMessageType, string> = {
    error: tx('错误', 'Error'),
    result: tx('结果', 'Result'),
    warning: tx('警告', 'Warning'),
    info: tx('日志', 'Log'),
  };

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="label" style={{ marginBottom: 8 }}>{title}</div>

      <div style={{ maxHeight, overflow: 'auto', display: 'grid', gap: 8 }}>
        {TYPE_ORDER.map((type) => {
          const group = messages.filter((m) => m.type === type);
          if (group.length === 0) return null;

          return (
            <div key={type} style={{ border: '1px solid var(--border-color)', borderRadius: 8, padding: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span className={TYPE_BADGE_CLASS[type]}>{typeLabel[type]}</span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {group.length} {tx('条', 'items')}
                </span>
              </div>

              <div style={{ display: 'grid', gap: 8, fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.6 }}>
                {group.map((m) => (
                  <div key={m.id} style={{ padding: 8, borderRadius: 6, background: 'var(--bg-primary)' }}>
                    {renderMessageBody(m.text, tx('展开', 'expand'))}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
