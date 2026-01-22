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

export interface ModelVersion {
  market: string;
  version_id: number;
  is_active: boolean;
  cv_score?: number;
  training_samples: number;
  trained_at?: string;
}

export interface ModelsResponse {
  versions: ModelVersion[];
}

export interface AutomationStatus {
  running: boolean;
  current_task?: string;
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
};
