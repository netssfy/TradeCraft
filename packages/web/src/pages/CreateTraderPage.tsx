import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { CreateTraderRequest } from '@tradecraft/shared/types';
import { createTraderSSE } from '../services/api';

interface FormErrors {
  id?: string;
  initial_cash?: string;
  allowed_symbols?: string;
}

export default function CreateTraderPage() {
  const navigate = useNavigate();
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
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!form.id.trim()) newErrors.id = '交易员 ID 不能为空';
    if (form.initial_cash <= 0) newErrors.initial_cash = '初始资金必须大于 0';
    if (form.allowed_symbols.length === 0) newErrors.allowed_symbols = '至少选择一个允许标的';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const addSymbol = () => {
    const sym = symbolInput.trim().toUpperCase();
    if (sym && !form.allowed_symbols.includes(sym)) {
      setForm((f) => ({ ...f, allowed_symbols: [...f.allowed_symbols, sym] }));
      setSymbolInput('');
    }
  };

  const removeSymbol = (sym: string) => {
    setForm((f) => ({
      ...f,
      allowed_symbols: form.allowed_symbols.filter((s) => s !== sym),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    setLogs([]);
    setError(null);

    try {
      await createTraderSSE(form, {
        onLog: (msg) => {
          setLogs((prev) => [...prev, msg]);
          setTimeout(() => logsEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
        },
        onResult: (trader) => {
          navigate(`/traders/${trader.id}`);
        },
        onError: (msg) => {
          setError(msg);
          setSubmitting(false);
        },
      });
    } catch (e: any) {
      if (e.message.includes('已存在')) {
        setError('交易员 ID 已存在');
      } else {
        setError(e.message);
      }
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 640 }}>
      <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 24 }}>创建交易员</h1>

      {error && <div className="error-message" style={{ marginBottom: 16 }}>{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="label">交易员 ID *</label>
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
          <label className="label">市场</label>
          <select
            className="input"
            value={form.market}
            onChange={(e) => setForm((f) => ({ ...f, market: e.target.value }))}
            disabled={submitting}
          >
            <option value="CN">CN (A股)</option>
            <option value="HK">HK (港股)</option>
            <option value="US">US (美股)</option>
          </select>
        </div>

        <div className="form-group">
          <label className="label">初始资金 *</label>
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
          <label className="label">允许标的 *</label>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input
              className="input"
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSymbol())}
              placeholder="输入股票代码，回车添加"
              disabled={submitting}
            />
            <button type="button" className="btn" onClick={addSymbol} disabled={submitting}>
              添加
            </button>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {form.allowed_symbols.map((sym) => (
              <span
                key={sym}
                className="badge"
                style={{
                  background: 'var(--bg-tertiary)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                }}
                onClick={() => !submitting && removeSymbol(sym)}
              >
                {sym} ×
              </span>
            ))}
          </div>
          {errors.allowed_symbols && <div className="form-error">{errors.allowed_symbols}</div>}
        </div>

        <div className="form-group">
          <label className="label">手续费率</label>
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
          <label className="label">订单超时（秒）</label>
          <input
            className="input mono"
            type="number"
            value={form.order_timeout_seconds}
            onChange={(e) => setForm((f) => ({ ...f, order_timeout_seconds: Number(e.target.value) }))}
            disabled={submitting}
          />
        </div>

        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? '创建中...' : '创建交易员'}
        </button>
      </form>

      {logs.length > 0 && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="label" style={{ marginBottom: 8 }}>AI 训练日志</div>
          <div
            style={{
              maxHeight: 300,
              overflow: 'auto',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              lineHeight: 1.6,
              color: 'var(--text-secondary)',
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
