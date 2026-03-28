import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { CreateTraderRequest } from '@tradecraft/shared/types';
import StreamMessagePanel, { type StreamMessage, type StreamMessageType } from '../components/StreamMessagePanel';
import { createTraderSSE } from '../services/api';

interface FormErrors {
  id?: string;
  initial_cash?: string;
  allowed_symbols?: string;
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

export default function CreateTraderPage() {
  const navigate = useNavigate();
  const nextMessageIdRef = useRef(1);

  const [form, setForm] = useState<CreateTraderRequest>({
    id: '',
    market: 'CN',
    initial_cash: 100000,
    allowed_symbols: [],
    commission_rate: 0.001,
    order_timeout_seconds: 300,
  });
  const [symbolInput, setSymbolInput] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

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

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!form.id.trim()) newErrors.id = 'Trader ID is required';
    if (form.initial_cash <= 0) newErrors.initial_cash = 'Initial cash must be greater than 0';
    if (form.allowed_symbols.length === 0) newErrors.allowed_symbols = 'Add at least one symbol';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const addSymbol = () => {
    const symbol = symbolInput.trim().toUpperCase();
    if (symbol && !form.allowed_symbols.includes(symbol)) {
      setForm((f) => ({ ...f, allowed_symbols: [...f.allowed_symbols, symbol] }));
      setSymbolInput('');
    }
  };

  const removeSymbol = (symbol: string) => {
    setForm((f) => ({
      ...f,
      allowed_symbols: f.allowed_symbols.filter((s) => s !== symbol),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    setMessages([]);
    setError(null);

    try {
      await createTraderSSE(form, {
        onLog: (msg) => appendLogLine(msg),
        onResult: (trader) => {
          appendMessage('result', `Trader created: ${trader.id}`);
          navigate(`/traders/${trader.id}`);
        },
        onError: (msg) => {
          appendMessage('error', msg);
          setError(msg);
          setSubmitting(false);
        },
      });
    } catch (e: any) {
      const msg = e?.message || 'Failed to create trader';
      appendMessage('error', msg);
      setError(msg);
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 760 }}>
      <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 24 }}>Create Trader</h1>

      {error && (
        <div className="error-message" style={{ marginBottom: 16 }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="label">Trader ID *</label>
          <input
            className="input"
            value={form.id}
            onChange={(e) => setForm((f) => ({ ...f, id: e.target.value }))}
            placeholder="my-trader"
            disabled={submitting}
          />
          {errors.id && <div className="form-error">{errors.id}</div>}
        </div>

        <div className="form-group">
          <label className="label">Market</label>
          <select
            className="input"
            value={form.market}
            onChange={(e) => setForm((f) => ({ ...f, market: e.target.value }))}
            disabled={submitting}
          >
            <option value="CN">CN</option>
            <option value="HK">HK</option>
            <option value="US">US</option>
          </select>
        </div>

        <div className="form-group">
          <label className="label">Initial Cash *</label>
          <input
            className="input mono"
            type="number"
            value={form.initial_cash}
            onChange={(e) => setForm((f) => ({ ...f, initial_cash: Number(e.target.value) }))}
            disabled={submitting}
          />
          {errors.initial_cash && <div className="form-error">{errors.initial_cash}</div>}
        </div>

        <div className="form-group">
          <label className="label">Allowed Symbols *</label>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input
              className="input"
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSymbol())}
              placeholder="Type symbol and press Enter"
              disabled={submitting}
            />
            <button type="button" className="btn" onClick={addSymbol} disabled={submitting}>
              Add
            </button>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {form.allowed_symbols.map((symbol) => (
              <span
                key={symbol}
                className="badge"
                style={{ background: 'var(--bg-tertiary)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}
                onClick={() => !submitting && removeSymbol(symbol)}
              >
                {symbol} x
              </span>
            ))}
          </div>
          {errors.allowed_symbols && <div className="form-error">{errors.allowed_symbols}</div>}
        </div>

        <div className="form-group">
          <label className="label">Commission Rate</label>
          <input
            className="input mono"
            type="number"
            step="0.0001"
            value={form.commission_rate}
            onChange={(e) => setForm((f) => ({ ...f, commission_rate: Number(e.target.value) }))}
            disabled={submitting}
          />
        </div>

        <div className="form-group">
          <label className="label">Order Timeout (seconds)</label>
          <input
            className="input mono"
            type="number"
            value={form.order_timeout_seconds}
            onChange={(e) => setForm((f) => ({ ...f, order_timeout_seconds: Number(e.target.value) }))}
            disabled={submitting}
          />
        </div>

        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Creating...' : 'Create Trader'}
        </button>
      </form>

      <StreamMessagePanel title="Create Stream Messages" messages={messages} />
    </div>
  );
}
