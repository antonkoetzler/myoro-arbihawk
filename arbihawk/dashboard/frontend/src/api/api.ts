import type {
  ToastType,
  HealthResponse,
  MetricsSummary,
  Bankroll,
  BetsResponse,
  TopConfidenceBetResponse,
  ModelsResponse,
  AutomationStatus,
  ErrorsResponse,
  DbStats,
  FakeMoneyConfig,
  ScraperWorkersConfig,
  TriggerAutomationParams,
  EnvironmentConfig,
  ImportResponse,
} from '../types';

/**
 * API functions factory
 * Creates API functions with integrated error handling and toast notifications
 */
export const createApi = (
  showToast: (message: string, type?: ToastType, duration?: number) => void
) => {
  const handleResponse = async <T>(response: Response): Promise<T> => {
    if (!response.ok) {
      const error = (await response
        .json()
        .catch(() => ({ detail: response.statusText }))) as {
          detail?: string;
          message?: string;
        };
      const message =
        error.detail ??
        error.message ??
        `Request failed: ${response.statusText}`;
      showToast(message, 'error');
      throw new Error(message);
    }
    return response.json() as Promise<T>;
  };

  const handleError = (err: unknown, defaultMessage: string): never => {
    const message = err instanceof Error ? err.message : defaultMessage;
    showToast(message, 'error');
    throw err;
  };

  return {
    getHealth: (): Promise<HealthResponse> =>
      fetch('/api/health')
        .then(handleResponse<HealthResponse>)
        .catch((err) => handleError(err, 'Failed to fetch health status')),

    getMetricsSummary: (): Promise<MetricsSummary> =>
      fetch('/api/metrics/summary')
        .then(handleResponse<MetricsSummary>)
        .catch((err) => handleError(err, 'Failed to fetch metrics')),

    getBankroll: (): Promise<Bankroll> =>
      fetch('/api/bankroll')
        .then(handleResponse<Bankroll>)
        .catch((err) => handleError(err, 'Failed to fetch bankroll')),

    getBets: (params?: {
      result?: string;
      market_name?: string;
      outcome_name?: string;
      tournament_name?: string;
      date_from?: string;
      date_to?: string;
      search?: string;
      page?: number;
      per_page?: number;
    }): Promise<BetsResponse> => {
      const queryParams = new URLSearchParams();
      if (params) {
        if (params.result) queryParams.append('result', params.result);
        if (params.market_name) queryParams.append('market_name', params.market_name);
        if (params.outcome_name) queryParams.append('outcome_name', params.outcome_name);
        if (params.tournament_name) queryParams.append('tournament_name', params.tournament_name);
        if (params.date_from) queryParams.append('date_from', params.date_from);
        if (params.date_to) queryParams.append('date_to', params.date_to);
        if (params.search) queryParams.append('search', params.search);
        if (params.page) queryParams.append('page', params.page.toString());
        if (params.per_page) queryParams.append('per_page', params.per_page.toString());
      }
      const queryString = queryParams.toString();
      return fetch(`/api/bets${queryString ? `?${queryString}` : ''}`)
        .then(handleResponse<BetsResponse>)
        .catch((err) => handleError(err, 'Failed to fetch bets'));
    },

    getBetFilterValues: (): Promise<{ markets: string[]; tournaments: string[] }> =>
      fetch('/api/bets/filter-values')
        .then(handleResponse<{ markets: string[]; tournaments: string[] }>)
        .catch((err) => handleError(err, 'Failed to fetch filter values')),

    getTopConfidenceBet: (
      sortBy?: 'confidence' | 'ev',
      limit?: number
    ): Promise<TopConfidenceBetResponse> => {
      const queryParams = new URLSearchParams();
      if (sortBy) queryParams.append('sort_by', sortBy);
      if (limit) queryParams.append('limit', limit.toString());
      const queryString = queryParams.toString();
      return fetch(`/api/bets/top-confidence${queryString ? `?${queryString}` : ''}`)
        .then(handleResponse<TopConfidenceBetResponse>)
        .catch((err) => handleError(err, 'Failed to fetch top confidence bet'));
    },

    getModels: (): Promise<ModelsResponse> =>
      fetch('/api/models')
        .then(handleResponse<ModelsResponse>)
        .catch((err) => handleError(err, 'Failed to fetch models')),

    getAutomationStatus: (): Promise<AutomationStatus> =>
      fetch('/api/automation/status')
        .then(handleResponse<AutomationStatus>)
        .catch((err) => handleError(err, 'Failed to fetch automation status')),

    getErrors: (): Promise<ErrorsResponse> =>
      fetch('/api/errors')
        .then(handleResponse<ErrorsResponse>)
        .catch((err) => handleError(err, 'Failed to fetch errors')),

    getDbStats: (): Promise<DbStats> =>
      fetch('/api/database/stats')
        .then(handleResponse<DbStats>)
        .catch((err) => handleError(err, 'Failed to fetch database stats')),

    resetDatabase: (preserveModels = true): Promise<{
      success: boolean;
      backup_path: string;
      records_deleted: Record<string, number>;
      total_deleted: number;
      preserved_models: boolean;
      model_versions_kept: number;
    }> =>
      fetch('/api/database/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preserve_models: preserveModels }),
      })
        .then(handleResponse<{
          success: boolean;
          backup_path: string;
          records_deleted: Record<string, number>;
          total_deleted: number;
          preserved_models: boolean;
          model_versions_kept: number;
        }>)
        .catch((err) => handleError(err, 'Failed to reset database')),

    triggerAutomation: (params: TriggerAutomationParams | string): Promise<unknown> => {
      // Support both old (string) and new (object) API for backwards compatibility
      const body = typeof params === 'string' ? { mode: params } : params;
      return fetch('/api/automation/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
        .then(handleResponse<unknown>)
        .catch((err) => handleError(err, 'Failed to trigger automation'));
    },

    stopAutomation: (): Promise<unknown> =>
      fetch('/api/automation/stop', { method: 'POST' })
        .then(handleResponse<unknown>)
        .catch((err) => handleError(err, 'Failed to stop automation')),

    startDaemon: (intervalSeconds = 21600): Promise<unknown> =>
      fetch('/api/automation/daemon/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_seconds: intervalSeconds }),
      })
        .then(handleResponse<unknown>)
        .catch((err) => handleError(err, 'Failed to start daemon')),

    getFakeMoneyConfig: (): Promise<FakeMoneyConfig> =>
      fetch('/api/config/fake-money')
        .then(handleResponse<FakeMoneyConfig>)
        .catch((err) => handleError(err, 'Failed to fetch fake money config')),

    updateFakeMoneyConfig: (
      config: Partial<FakeMoneyConfig>
    ): Promise<FakeMoneyConfig> =>
      fetch('/api/config/fake-money', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
        .then(handleResponse<FakeMoneyConfig>)
        .catch((err) => handleError(err, 'Failed to update fake money config')),

    dismissError: (
      errorType: string,
      errorId: number | null,
      errorKey: string | null
    ): Promise<unknown> => {
      const params = new URLSearchParams({ error_type: errorType });
      if (errorId !== null) params.append('error_id', errorId.toString());
      if (errorKey !== null) params.append('error_key', errorKey);
      return fetch(`/api/errors/dismiss?${params}`, { method: 'POST' })
        .then(handleResponse<unknown>)
        .catch((err) => handleError(err, 'Failed to dismiss error'));
    },

    getScraperWorkersConfig: (): Promise<ScraperWorkersConfig> =>
      fetch('/api/config/scraper-workers')
        .then(handleResponse<ScraperWorkersConfig>)
        .catch((err) =>
          handleError(err, 'Failed to fetch scraper workers config')
        ),

    updateScraperWorkersConfig: (
      config: Partial<ScraperWorkersConfig>
    ): Promise<ScraperWorkersConfig> =>
      fetch('/api/config/scraper-workers', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
        .then(handleResponse<ScraperWorkersConfig>)
        .catch((err) =>
          handleError(err, 'Failed to update scraper workers config')
        ),

    getEnvironment: (): Promise<EnvironmentConfig> =>
      fetch('/api/config/environment')
        .then(handleResponse<EnvironmentConfig>)
        .catch((err) => handleError(err, 'Failed to fetch environment config')),

    updateEnvironment: (
      environment: 'debug' | 'production'
    ): Promise<EnvironmentConfig> =>
      fetch('/api/config/environment', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ environment }),
      })
        .then(handleResponse<EnvironmentConfig>)
        .catch((err) => handleError(err, 'Failed to update environment')),

    syncProdToDebug: (): Promise<{
      success: boolean;
      records_copied: Record<string, number>;
      total_copied: number;
      source_db: string;
      target_db: string;
    }> =>
      fetch('/api/database/sync-prod-to-debug', {
        method: 'POST',
      })
        .then(handleResponse<{
          success: boolean;
          records_copied: Record<string, number>;
          total_copied: number;
          source_db: string;
          target_db: string;
        }>)
        .catch((err) => handleError(err, 'Failed to sync production to debug')),

    exportData: async (): Promise<void> => {
      try {
        const response = await fetch('/api/export');
        if (!response.ok) {
          const error = (await response.json().catch(() => ({ detail: response.statusText }))) as {
            detail?: string;
          };
          throw new Error(error.detail ?? 'Export failed');
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const contentDisposition = response.headers.get('Content-Disposition');
        const filename = contentDisposition
          ? contentDisposition.split('filename=')[1]?.replace(/"/g, '') || 'arbihawk_export.zip'
          : 'arbihawk_export.zip';
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showToast('Export completed successfully', 'success');
      } catch (err) {
        handleError(err, 'Failed to export data');
      }
    },

    importData: async (
      file: File,
      overwriteDb: boolean,
      overwriteModels: boolean,
      overwriteConfig: boolean
    ): Promise<ImportResponse> => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('overwrite_db', overwriteDb.toString());
      formData.append('overwrite_models', overwriteModels.toString());
      formData.append('overwrite_config', overwriteConfig.toString());

      return fetch('/api/import', {
        method: 'POST',
        body: formData,
      })
        .then(async (response) => {
          if (!response.ok) {
            const error = (await response.json().catch(() => ({ detail: response.statusText }))) as {
              detail?: string;
            };
            throw new Error(error.detail ?? 'Import failed');
          }
          return response.json() as Promise<ImportResponse>;
        })
        .then((data) => {
          if (data.success) {
            showToast('Import completed successfully', 'success', 10000);
          }
          return data;
        })
        .catch((err) => handleError(err, 'Failed to import data'));
    },

    // Trading API
    triggerTradingCollection: (): Promise<{ success: boolean; message?: string; error?: string }> =>
      fetch('/api/trading/collect', {
        method: 'POST',
      })
        .then(handleResponse<{ success: boolean; message?: string; error?: string }>)
        .catch((err) => handleError(err, 'Failed to trigger trading collection')),

    getTradingStatus: (): Promise<import('../types').TradingStatus> =>
      fetch('/api/trading/status')
        .then(handleResponse<import('../types').TradingStatus>)
        .catch((err) => handleError(err, 'Failed to fetch trading status')),

    triggerTradingTraining: (): Promise<{ success: boolean; message?: string; error?: string }> =>
      fetch('/api/trading/train', { method: 'POST' })
        .then(handleResponse<{ success: boolean; message?: string; error?: string }>)
        .catch((err) => handleError(err, 'Failed to trigger trading training')),

    triggerTradingCycle: (): Promise<{ success: boolean; message?: string; error?: string }> =>
      fetch('/api/trading/cycle', { method: 'POST' })
        .then(handleResponse<{ success: boolean; message?: string; error?: string }>)
        .catch((err) => handleError(err, 'Failed to trigger trading cycle')),

    triggerFullTradingCycle: (): Promise<{ success: boolean; message?: string; error?: string }> =>
      fetch('/api/trading/full', { method: 'POST' })
        .then(handleResponse<{ success: boolean; message?: string; error?: string }>)
        .catch((err) => handleError(err, 'Failed to trigger full trading cycle')),

    startTradingDaemon: (
      intervalSeconds: number = 3600
    ): Promise<{ success: boolean; message?: string; error?: string }> =>
      fetch('/api/trading/daemon/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_seconds: intervalSeconds }),
      })
        .then(handleResponse<{ success: boolean; message?: string; error?: string }>)
        .catch((err) => handleError(err, 'Failed to start trading daemon')),

    stopTradingDaemon: (): Promise<{ success: boolean; message?: string; error?: string }> =>
      fetch('/api/trading/daemon/stop', { method: 'POST' })
        .then(handleResponse<{ success: boolean; message?: string; error?: string }>)
        .catch((err) => handleError(err, 'Failed to stop trading daemon')),

    getTradingPortfolio: (): Promise<{
      cash_balance: number;
      portfolio_value: number;
      available_cash: number;
      positions_count: number;
      realized_pnl: number;
      unrealized_pnl: number;
      total_pnl: number;
      error?: string;
    }> =>
      fetch('/api/trading/portfolio')
        .then(handleResponse<{
          cash_balance: number;
          portfolio_value: number;
          available_cash: number;
          positions_count: number;
          realized_pnl: number;
          unrealized_pnl: number;
          total_pnl: number;
          error?: string;
        }>)
        .catch((err) => handleError(err, 'Failed to fetch trading portfolio')),

    getTradingPositions: (): Promise<{
      positions: Array<{
        id: number;
        symbol: string;
        asset_type: string;
        strategy: string;
        direction: string;
        quantity: number;
        entry_price: number;
        current_price: number;
        unrealized_pnl: number;
        pnl_pct: number;
        stop_loss?: number;
        take_profit?: number;
        opened_at: string;
      }>;
      count: number;
      error?: string;
    }> =>
      fetch('/api/trading/positions')
        .then(handleResponse<{
          positions: Array<{
            id: number;
            symbol: string;
            asset_type: string;
            strategy: string;
            direction: string;
            quantity: number;
            entry_price: number;
            current_price: number;
            unrealized_pnl: number;
            pnl_pct: number;
            stop_loss?: number;
            take_profit?: number;
            opened_at: string;
          }>;
          count: number;
          error?: string;
        }>)
        .catch((err) => handleError(err, 'Failed to fetch trading positions')),

    getTradingTrades: (limit = 50): Promise<{
      trades: Array<{
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
      }>;
      count: number;
      error?: string;
    }> =>
      fetch(`/api/trading/trades?limit=${limit}`)
        .then(handleResponse<{
          trades: Array<{
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
          }>;
          count: number;
          error?: string;
        }>)
        .catch((err) => handleError(err, 'Failed to fetch trading trades')),

    getTradingSignals: (limit = 10): Promise<{
      signals: Array<{
        symbol: string;
        asset_type: string;
        strategy: string;
        direction: string;
        confidence: number;
        entry_price: number;
        stop_loss: number;
        take_profit: number;
        risk_reward: number;
        expected_value: number;
        timestamp: string;
      }>;
      count: number;
      error?: string;
    }> =>
      fetch(`/api/trading/signals?limit=${limit}`)
        .then(handleResponse<{
          signals: Array<{
            symbol: string;
            asset_type: string;
            strategy: string;
            direction: string;
            confidence: number;
            entry_price: number;
            stop_loss: number;
            take_profit: number;
            risk_reward: number;
            expected_value: number;
            timestamp: string;
          }>;
          count: number;
          error?: string;
        }>)
        .catch((err) => handleError(err, 'Failed to fetch trading signals')),

    getTradingPerformance: (): Promise<{
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
    }> =>
      fetch('/api/trading/performance')
        .then(handleResponse<{
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
        }>)
        .catch((err) => handleError(err, 'Failed to fetch trading performance')),

    getTradingModels: (): Promise<Record<string, {
      available: boolean;
      path: string;
      version?: string;
      cv_score?: number;
      created_at?: string;
    }>> =>
      fetch('/api/trading/models')
        .then(handleResponse<Record<string, {
          available: boolean;
          path: string;
          version?: string;
          cv_score?: number;
          created_at?: string;
        }>>)
        .catch((err) => handleError(err, 'Failed to fetch trading models')),

    closePosition: (symbol: string): Promise<{ success: boolean; error?: string }> =>
      fetch('/api/trading/positions/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol }),
      })
        .then(handleResponse<{ success: boolean; error?: string }>)
        .catch((err) => handleError(err, 'Failed to close position')),

    initializeTradingPortfolio: (startingBalance?: number): Promise<{ success: boolean; error?: string }> =>
      fetch('/api/trading/portfolio/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ starting_balance: startingBalance }),
      })
        .then(handleResponse<{ success: boolean; error?: string }>)
        .catch((err) => handleError(err, 'Failed to initialize portfolio')),

    updateTradingWatchlist: (data: { stocks?: string[], crypto?: string[] }): Promise<{ success: boolean; watchlist: any }> =>
      fetch('/api/trading/watchlist', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
        .then(handleResponse<{ success: boolean; watchlist: any }>)
        .catch((err) => handleError(err, 'Failed to update watchlist')),
  };
};
