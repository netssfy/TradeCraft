export interface Traits {
  risk_appetite: string;
  holding_horizon: string;
  signal_preference: string;
  position_construction: string;
  exit_discipline: string;
  universe_focus: string;
}

export interface Trader {
  id: string;
  market: string;
  initial_cash: number;
  allowed_symbols: string[];
  commission_rate: number;
  order_timeout_seconds: number;
  active_strategy: string;
  traits: Traits;
}

export interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
}

export interface PortfolioSnapshot {
  date: string;
  cash: number;
  positions: Record<string, Position>;
}

export interface Portfolio {
  trader_id: string;
  mode: string;
  snapshots: PortfolioSnapshot[];
}

export interface Trade {
  timestamp: string;
  symbol: string;
  direction: 'buy' | 'sell';
  quantity: number;
  price: number;
  commission: number;
}

export interface StrategyFile {
  filename: string;
  is_active: boolean;
}

export interface CreateTraderRequest {
  id: string;
  market: string;
  initial_cash: number;
  allowed_symbols: string[];
  commission_rate: number;
  order_timeout_seconds: number;
}

export interface UpdateTraderRequest {
  initial_cash?: number;
  allowed_symbols?: string[];
  commission_rate?: number;
  order_timeout_seconds?: number;
  traits?: Traits;
}

export interface TradeRuns {
  paper: string[];
  backtest: string[];
}
