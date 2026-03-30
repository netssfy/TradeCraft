import { useState } from 'react';
import type { Trader, UpdateTraderRequest } from '@tradecraft/shared/types';
import { TRAIT_LABELS } from '@tradecraft/shared/utils';
import { useI18n } from '../hooks/useI18n';
import { api } from '../services/api';

interface EditTraderModalProps {
  trader: Trader;
  onClose: () => void;
  onUpdated: (trader: Trader) => void;
}

export default function EditTraderModal({ trader, onClose, onUpdated }: EditTraderModalProps) {
  const { tx } = useI18n();
  const [form, setForm] = useState<UpdateTraderRequest>({
    initial_cash: trader.initial_cash,
    allowed_symbols: trader.allowed_symbols,
    commission_rate: trader.commission_rate,
    order_timeout_seconds: trader.order_timeout_seconds,
    traits: { ...trader.traits },
  });
  const [symbolInput, setSymbolInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateTrader(trader.id, form);
      onUpdated(updated);
    } catch (e: any) {
      setError(e.message);
      setSaving(false);
    }
  };

  const addSymbol = () => {
    const sym = symbolInput.trim().toUpperCase();
    if (sym && form.allowed_symbols && !form.allowed_symbols.includes(sym)) {
      setForm((f) => ({ ...f, allowed_symbols: [...(f.allowed_symbols || []), sym] }));
      setSymbolInput('');
    }
  };

  const removeSymbol = (sym: string) => {
    setForm((f) => ({
      ...f,
      allowed_symbols: (f.allowed_symbols || []).filter((s) => s !== sym),
    }));
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(4, 10, 20, 0.6)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div className="card" style={{ width: '90%', maxWidth: 520, maxHeight: '90vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>{tx('编辑交易员', 'Edit Trader')}</h2>

        {error && <div className="error-message" style={{ marginBottom: 16 }}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="label">{tx('初始资金', 'Initial Cash')}</label>
            <input
              className="input mono"
              type="number"
              value={form.initial_cash}
              onChange={(e) => setForm((f) => ({ ...f, initial_cash: Number(e.target.value) }))}
              disabled={saving}
            />
          </div>

          <div className="form-group">
            <label className="label">{tx('允许标的', 'Allowed Symbols')}</label>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <input
                className="input"
                value={symbolInput}
                onChange={(e) => setSymbolInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSymbol())}
                placeholder={tx('输入股票代码后回车添加', 'Type symbol and press Enter')}
                disabled={saving}
              />
              <button type="button" className="btn" onClick={addSymbol} disabled={saving}>
                {tx('添加', 'Add')}
              </button>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {(form.allowed_symbols || []).map((sym) => (
                <span key={sym} className="badge" style={{ background: 'var(--bg-tertiary)', cursor: 'pointer' }} onClick={() => !saving && removeSymbol(sym)}>
                  {sym} ×
                </span>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label className="label">{tx('手续费率', 'Commission Rate')}</label>
            <input
              className="input mono"
              type="number"
              step="0.0001"
              value={form.commission_rate}
              onChange={(e) => setForm((f) => ({ ...f, commission_rate: Number(e.target.value) }))}
              disabled={saving}
            />
          </div>

          <div className="form-group">
            <label className="label">{tx('订单超时（秒）', 'Order Timeout (seconds)')}</label>
            <input
              className="input mono"
              type="number"
              value={form.order_timeout_seconds}
              onChange={(e) => setForm((f) => ({ ...f, order_timeout_seconds: Number(e.target.value) }))}
              disabled={saving}
            />
          </div>

          <div className="label" style={{ marginBottom: 8 }}>{tx('六维特质', 'Traits')}</div>
          {form.traits &&
            Object.entries(form.traits).map(([key, value]) => (
              <div key={key} className="form-group">
                <label className="label">{TRAIT_LABELS[key] || key}</label>
                <input
                  className="input"
                  value={value}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      traits: { ...f.traits!, [key]: e.target.value },
                    }))
                  }
                  disabled={saving}
                />
              </div>
            ))}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 24 }}>
            <button type="button" className="btn" onClick={onClose} disabled={saving}>
              {tx('取消', 'Cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? tx('保存中...', 'Saving...') : tx('保存', 'Save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
