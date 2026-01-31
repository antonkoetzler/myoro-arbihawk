// API Response Types
export interface HealthResponse {
  status: 'healthy' | 'unhealthy' | 'degraded';
}

export type MetricsSummary = Record<string, unknown>;

export interface Bankroll {
  current_balance: number;
  starting_balance: number;
  profit: number;
  roi: number;
  win_rate: number;
  wins: number;
  losses: number;
  total_bets: number;
  pending_bets: number;
  by_model?: Record<
    string,
    {
      total_bets: number;
      win_rate: number;
      roi: number;
      profit: number;
    }
  >;
}

export interface Bet {
  market_name?: string;
  outcome_name?: string;
  model_market?: string;
  odds: number;
  stake: number;
  payout?: number;
  result?: 'win' | 'loss' | 'pending';
  tournament_name?: string;
  placed_at?: string;
}

export interface BetsResponse {
  bets: Bet[];
  count: number;
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface TopConfidenceBet {
  fixture_id: string;
  home_team: string;
  away_team: string;
  start_time: string;
  market: string;
  market_display?: string;
  outcome: string;
  outcome_display?: string;
  odds: number;
  probability: number;
  expected_value: number;
  bookmaker: string;
  tournament_name?: string;
}

export interface TopConfidenceBetResponse {
  bets: TopConfidenceBet[];
  count: number;
  sort_by?: string;
  message?: string;
}

export interface ModelVersion {
  market: string;
  version_id: number;
  is_active: boolean;
  cv_score?: number;
  training_samples: number;
  trained_at?: string;
  brier_score?: number;
  ece?: number;
  calibration_improvement?: {
    brier_score?: number;
    ece?: number;
  };
  performance_metrics?: Record<string, unknown>;
}

export interface ModelsResponse {
  versions: ModelVersion[];
}

export interface AutomationStatus {
  running: boolean;
  trading_daemon_running?: boolean;
  current_task?: string;
  stopping?: boolean;  // True when stop signal has been sent
  last_collection?: string;
  last_training?: string;
  last_betting?: string;
  // Performance metrics
  last_collection_duration_seconds?: number;
  last_training_duration_seconds?: number;
  last_betting_duration_seconds?: number;
  last_full_run_duration_seconds?: number;
  scraper_durations_seconds?: Record<string, number>;
}

export interface LogError {
  timestamp: string;
  message: string;
}

export interface IngestionError {
  id?: number;
  source: string;
  errors: string;
}

export interface ErrorsResponse {
  total_errors: number;
  log_errors?: LogError[];
  ingestion_errors?: IngestionError[];
}

export type DbStats = Record<string, number | string>;

export interface FakeMoneyConfig {
  auto_bet_after_training: boolean;
  starting_balance: number;
  bet_sizing_strategy: 'fixed' | 'percentage';
  fixed_stake?: number;
  percentage_stake?: number;
}

export interface ScraperWorkersConfig {
  max_workers_leagues: number;
  max_workers_odds: number;
  max_workers_leagues_playwright?: number;
}

export interface EnvironmentConfig {
  environment: 'debug' | 'production';
  db_path: string;
}

export interface ImportResponse {
  success: boolean;
  message: string;
  version_info?: {
    exported_at?: string;
    schema_version?: number;
    platform?: {
      system?: string;
      release?: string;
      machine?: string;
      python_version?: string;
    };
  };
  schema_warning?: string;
  imported: {
    database: boolean;
    models: string[];
    configs: string[];
  };
  skipped: {
    models: string[];
    configs: string[];
  };
  backup_path?: string;
}

export interface TriggerAutomationParams {
  mode: string;
  max_workers_leagues?: number;
  max_workers_odds?: number;
  max_workers_leagues_playwright?: number;
}

// WebSocket Types
export interface WebSocketLog {
  timestamp: string;
  level?: 'error' | 'warning' | 'info' | 'success' | 'ok';
  message: string;
  type?: string;
  domain?: 'betting' | 'trading';
}

// Trading Types
export interface TradingPortfolio {
  cash_balance: number;
  portfolio_value: number;
  available_cash: number;
  positions_count: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  error?: string;
}

export interface TradingPosition {
  id: number;
  symbol: string;
  asset_type: string;
  strategy: string;
  direction: 'long' | 'short';
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_pct: number;
  stop_loss?: number;
  take_profit?: number;
  opened_at: string;
}

export interface TradingTrade {
  id: number;
  symbol: string;
  asset_type: string;
  strategy: string;
  direction: string;
  order_type: string;
  quantity: number;
  price: number;
  pnl?: number;
  timestamp: string;
}

export interface TradingSignal {
  symbol: string;
  asset_type: string;
  strategy: string;
  direction: 'long' | 'short';
  confidence: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  risk_reward: number;
  expected_value: number;
  timestamp: string;
}

export interface TradingPerformance {
  roi: number;
  total_return: number;
  win_rate: number;
  profit: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: number;
  avg_loss: number;
  sharpe_ratio: number;
  max_drawdown: number;
  current_value: number;
  starting_balance: number;
  error?: string;
}

export interface TradingModelStatus {
  [strategy: string]: {
    available: boolean;
    path: string;
    version?: string;
    cv_score?: number;
    created_at?: string;
  };
}

export interface TradingStatus {
  enabled: boolean;
  current_task?: string | null;
  last_collection?: string;
  last_collection_duration_seconds?: number;
  watchlist: {
    stocks: string[];
    crypto: string[];
  };
  api_keys_configured: {
    alpha_vantage: boolean;
    coingecko: boolean;
  };
}

// Toast Types
export type ToastType = 'error' | 'success' | 'info';

// Component Prop Types
export interface TooltipProps {
  text?: string;
  children: React.ReactNode;
  className?: string;
  position?: 'auto' | 'top' | 'bottom' | 'left' | 'right';
}

export interface EmptyStateProps {
  icon: React.ComponentType<{ size?: number | string; className?: string }>;
  title: string;
  description?: string;
}

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<{ size?: number | string; className?: string }>;
  trend?: 'up' | 'down' | null;
}

// API Function Types
export type ApiFunction = (
  showToast: (message: string, type?: ToastType, duration?: number) => void
) => {
  getHealth: () => Promise<HealthResponse>;
  getMetricsSummary: () => Promise<MetricsSummary>;
  getBankroll: () => Promise<Bankroll>;
  getBets: (limit?: number) => Promise<BetsResponse>;
  getModels: () => Promise<ModelsResponse>;
  getAutomationStatus: () => Promise<AutomationStatus>;
  getErrors: () => Promise<ErrorsResponse>;
  getDbStats: () => Promise<DbStats>;
  triggerAutomation: (mode: string) => Promise<unknown>;
  stopAutomation: () => Promise<unknown>;
  startDaemon: (intervalSeconds?: number) => Promise<unknown>;
  getFakeMoneyConfig: () => Promise<FakeMoneyConfig>;
  updateFakeMoneyConfig: (
    config: Partial<FakeMoneyConfig>
  ) => Promise<FakeMoneyConfig>;
  dismissError: (
    errorType: string,
    errorId: number | null,
    errorKey: string | null
  ) => Promise<unknown>;
  getEnvironment: () => Promise<EnvironmentConfig>;
  updateEnvironment: (environment: 'debug' | 'production') => Promise<EnvironmentConfig>;
};
