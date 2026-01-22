import type {
  ToastType,
  HealthResponse,
  MetricsSummary,
  Bankroll,
  BetsResponse,
  ModelsResponse,
  AutomationStatus,
  ErrorsResponse,
  DbStats,
  FakeMoneyConfig,
  ScraperWorkersConfig,
  TriggerAutomationParams,
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
  };
};
