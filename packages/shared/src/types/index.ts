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

export interface StrategyCode {
  filename: string;
  code: string;
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

export interface BacktestMetrics {
  annualized_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  profit_loss_ratio: number;
}

export interface BacktestReport {
  trader_id: string;
  backtest_start: string;
  backtest_end: string;
  initial_cash: number;
  final_nav: number;
  strategy_filename?: string | null;
  metrics: BacktestMetrics;
}

export interface MarketDataItem {
  market: string;
  symbol: string;
  interval: string;
  file_count: number;
  start_period: string | null;
  end_period: string | null;
  periods: string[];
}

export interface MarketDataAvailability {
  root: string;
  total_files: number;
  items: MarketDataItem[];
}

export type MarketDataFileValue = string | number | boolean | null;

export interface MarketDataFileDetail {
  market: string;
  symbol: string;
  interval: string;
  period: string;
  path: string;
  columns: string[];
  total_rows: number;
  page: number;
  page_size: number;
  rows: Record<string, MarketDataFileValue>[];
}
