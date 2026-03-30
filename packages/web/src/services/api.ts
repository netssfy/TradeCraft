import type {
  Trader,
  Portfolio,
  StrategyFile,
  StrategyCode,
  Trade,
  TradeRuns,
  BacktestReport,
  CreateTraderRequest,
  UpdateTraderRequest,
} from '@tradecraft/shared/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listTraders: () => request<Trader[]>('/traders'),

  getTrader: (id: string) => request<Trader>(`/traders/${id}`),

  updateTrader: (id: string, data: UpdateTraderRequest) =>
    request<Trader>(`/traders/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteTrader: (id: string) =>
    request<void>(`/traders/${id}`, { method: 'DELETE' }),

  getPortfolio: (id: string, mode: string, runId?: string) =>
    request<Portfolio>(
      `/traders/${id}/portfolio/${mode}${runId ? `?run_id=${encodeURIComponent(runId)}` : ''}`
    ),

  listStrategies: (id: string) =>
    request<StrategyFile[]>(`/traders/${id}/strategy`),

  getStrategyCode: (id: string, filename: string) =>
    request<StrategyCode>(`/traders/${id}/strategy/${encodeURIComponent(filename)}/code`),

  uploadStrategy: async (id: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE}/traders/${id}/strategy`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`${res.status}: ${body}`);
    }
    return res.json() as Promise<StrategyFile>;
  },

  setActiveStrategy: (id: string, filename: string) =>
    request<Trader>(
      `/traders/${id}/strategy/active?filename=${encodeURIComponent(filename)}`,
      { method: 'PUT' }
    ),

  listTradeRuns: (id: string) => request<TradeRuns>(`/traders/${id}/trades`),

  getTrades: (id: string, mode: string, runId: string) =>
    request<Trade[]>(`/traders/${id}/trades/${mode}/${runId}`),

  getBacktestReport: (id: string, runId: string) =>
    request<BacktestReport>(`/traders/${id}/backtest/report/${runId}`),

  deleteBacktestRun: (id: string, runId: string) =>
    request<void>(`/traders/${id}/backtest/run/${runId}`, { method: 'DELETE' }),

  runBacktest: (
    id: string,
    range?: { start_date?: string; end_date?: string; strategy_filename?: string }
  ) =>
    request<{ trader_id: string; run_id: string }>(`/traders/${id}/backtest/run`, {
      method: 'POST',
      body: JSON.stringify(range ?? {}),
    }),
};

export interface SSECallbacks {
  onLog?: (message: string) => void;
  onResult?: (trader: Trader) => void;
  onError?: (message: string) => void;
}

export interface ResearchSSECallbacks {
  onLog?: (message: string) => void;
  onResult?: (data: { trader_id: string; strategies: string[] }) => void;
  onError?: (message: string) => void;
}

export interface ResearchStrategyOptions {
  mode?: 'create' | 'update';
  target?: string;
}

export async function createTraderSSE(
  data: CreateTraderRequest,
  callbacks: SSECallbacks
): Promise<void> {
  const res = await fetch(`${API_BASE}/traders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!res.ok && res.status !== 201) {
    if (res.status === 409) {
      throw new Error('交易员 ID 已存在');
    }
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('无法读取响应流');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    let currentEvent = '';
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        const data = line.slice(6);
        try {
          const payload = JSON.parse(data);
          if (currentEvent === 'log' && callbacks.onLog) {
            callbacks.onLog(payload.message);
          } else if (currentEvent === 'result' && callbacks.onResult) {
            callbacks.onResult(payload);
          } else if (currentEvent === 'error' && callbacks.onError) {
            callbacks.onError(payload.message);
          }
        } catch {}
      }
    }
  }
}

export async function researchStrategySSE(
  traderId: string,
  callbacks: ResearchSSECallbacks,
  options?: ResearchStrategyOptions
): Promise<void> {
  const params = new URLSearchParams();
  if (options?.mode) params.set('mode', options.mode);
  if (options?.target) params.set('target', options.target);
  const query = params.toString();
  const url = `${API_BASE}/traders/${traderId}/strategy/research${query ? `?${query}` : ''}`;
  const res = await fetch(url, {
    method: 'POST',
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('无法读取响应流');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    let currentEvent = '';
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        const data = line.slice(6);
        try {
          const payload = JSON.parse(data);
          if (currentEvent === 'log' && callbacks.onLog) {
            callbacks.onLog(payload.message);
          } else if (currentEvent === 'result' && callbacks.onResult) {
            callbacks.onResult(payload);
          } else if (currentEvent === 'error' && callbacks.onError) {
            callbacks.onError(payload.message);
          }
        } catch {}
      }
    }
  }
}
