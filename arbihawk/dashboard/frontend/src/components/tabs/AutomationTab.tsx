import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, Square, RefreshCw, TrendingUp, Settings } from 'lucide-react';
import { Tooltip } from '../Tooltip';
import type { createApi } from '../../api/api';
import type {
  ToastType,
  AutomationStatus,
  FakeMoneyConfig,
  ScraperWorkersConfig,
} from '../../types';

interface AutomationTabProps {
  api: ReturnType<typeof createApi>;
  showToast: (message: string, type?: ToastType, duration?: number) => void;
  onSwitchToLogs?: () => void;
}

/**
 * Automation tab component - displays automation controls and configuration
 */
export function AutomationTab({
  api,
  showToast,
  onSwitchToLogs,
}: AutomationTabProps) {
  const queryClient = useQueryClient();

  const { data: status } = useQuery<AutomationStatus>({
    queryKey: ['status'],
    queryFn: api.getAutomationStatus,
    refetchInterval: 30000,
    retry: false,
  });

  const { data: fakeMoneyConfig } = useQuery<FakeMoneyConfig>({
    queryKey: ['fakeMoneyConfig'],
    queryFn: api.getFakeMoneyConfig,
    refetchInterval: false,
    retry: false,
  });

  const { data: scraperWorkersConfig } = useQuery<ScraperWorkersConfig>({
    queryKey: ['scraperWorkersConfig'],
    queryFn: api.getScraperWorkersConfig,
    refetchInterval: false,
    retry: false,
  });

  // Local state for worker counts (use config values as defaults)
  const [workersLeagues, setWorkersLeagues] = useState<number | undefined>(
    undefined
  );
  const [workersOdds, setWorkersOdds] = useState<number | undefined>(undefined);
  const [workersPlaywright, setWorkersPlaywright] = useState<number | undefined>(
    undefined
  );

  // Effective worker values (local state or config)
  const effectiveWorkersLeagues =
    workersLeagues ?? scraperWorkersConfig?.max_workers_leagues ?? 5;
  const effectiveWorkersOdds =
    workersOdds ?? scraperWorkersConfig?.max_workers_odds ?? 5;
  const effectiveWorkersPlaywright =
    workersPlaywright ?? scraperWorkersConfig?.max_workers_leagues_playwright ?? 3;

  const triggerMutation = useMutation({
    mutationFn: api.triggerAutomation,
    onSuccess: (_data, params) => {
      void queryClient.invalidateQueries({ queryKey: ['status'] });
      // Invalidate bets and bankroll queries for modes that might affect them
      const mode = typeof params === 'string' ? params : params.mode;
      if (mode === 'betting' || mode === 'full') {
        void queryClient.invalidateQueries({ queryKey: ['bets'] });
        void queryClient.invalidateQueries({ queryKey: ['bankroll'] });
      }
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to trigger automation', 'error');
    },
  });

  const updateScraperWorkersMutation = useMutation({
    mutationFn: api.updateScraperWorkersConfig,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['scraperWorkersConfig'] });
      showToast('Scraper worker settings saved', 'success');
    },
    onError: (error: Error) => {
      showToast(
        error.message ?? 'Failed to update scraper workers config',
        'error'
      );
    },
  });

  // Trigger collection with worker overrides
  const triggerCollectionWithWorkers = () => {
    if (onSwitchToLogs) onSwitchToLogs();
    triggerMutation.mutate({
      mode: 'collect',
      max_workers_leagues: effectiveWorkersLeagues,
      max_workers_odds: effectiveWorkersOdds,
    });
  };

  // Trigger full run with worker overrides
  const triggerFullRunWithWorkers = () => {
    if (onSwitchToLogs) onSwitchToLogs();
    triggerMutation.mutate({
      mode: 'full',
      max_workers_leagues: effectiveWorkersLeagues,
      max_workers_odds: effectiveWorkersOdds,
    });
  };

  const stopMutation = useMutation({
    mutationFn: api.stopAutomation,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['status'] });
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to stop automation', 'error');
    },
  });

  const updateFakeMoneyMutation = useMutation({
    mutationFn: api.updateFakeMoneyConfig,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['fakeMoneyConfig'] });
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to update fake money config', 'error');
    },
  });

  const startDaemonMutation = useMutation({
    mutationFn: () => api.startDaemon(21600),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['status'] });
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to start daemon', 'error');
    },
  });

  const isTaskRunning = !!status?.current_task;
  const taskButtonTooltip = isTaskRunning
    ? 'You can only run one task at a time'
    : '';
  const stopButtonTooltip = !isTaskRunning
    ? 'No task is currently running'
    : '';

  return (
    <div className='space-y-6'>
      <div className='card'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='text-lg font-semibold'>Automation Control</h3>
          <div
            className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm ${status?.running ? 'bg-sky-500/20 text-sky-400' : 'bg-slate-700 text-slate-400'}`}
          >
            {status?.running ? 'Running' : 'Stopped'}
          </div>
        </div>

        <div className='mb-6 grid grid-cols-1 gap-4 md:grid-cols-4'>
          <div className='rounded-lg bg-slate-700/30 p-4'>
            <p className='text-sm text-slate-400'>Current Task</p>
            <p className='font-medium'>{status?.current_task ?? 'None'}</p>
          </div>
          <div className='rounded-lg bg-slate-700/30 p-4'>
            <p className='text-sm text-slate-400'>Last Collection</p>
            <p className='font-mono text-sm font-medium'>
              {status?.last_collection
                ? new Date(status.last_collection).toLocaleString()
                : 'Never'}
            </p>
            {status?.last_collection_duration_seconds != null && (
              <p className='mt-1 text-xs text-slate-500'>
                Duration:{' '}
                {status.last_collection_duration_seconds >= 60
                  ? `${(status.last_collection_duration_seconds / 60).toFixed(1)} min`
                  : `${status.last_collection_duration_seconds.toFixed(1)}s`}
              </p>
            )}
          </div>
          <div className='rounded-lg bg-slate-700/30 p-4'>
            <p className='text-sm text-slate-400'>Last Training</p>
            <p className='font-mono text-sm font-medium'>
              {status?.last_training
                ? new Date(status.last_training).toLocaleString()
                : 'Never'}
            </p>
            {status?.last_training_duration_seconds != null && (
              <p className='mt-1 text-xs text-slate-500'>
                Duration: {status.last_training_duration_seconds.toFixed(1)}s
              </p>
            )}
          </div>
          <div className='rounded-lg bg-slate-700/30 p-4'>
            <p className='text-sm text-slate-400'>Last Betting</p>
            <p className='font-mono text-sm font-medium'>
              {status?.last_betting
                ? new Date(status.last_betting).toLocaleString()
                : 'Never'}
            </p>
            {status?.last_betting_duration_seconds != null && (
              <p className='mt-1 text-xs text-slate-500'>
                Duration: {status.last_betting_duration_seconds.toFixed(1)}s
              </p>
            )}
          </div>
        </div>

        <div className='flex flex-wrap gap-3'>
          <Tooltip text={taskButtonTooltip}>
            <button
              onClick={triggerCollectionWithWorkers}
              disabled={triggerMutation.isPending || isTaskRunning}
              className='btn-primary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
              type='button'
            >
              <Play size={16} /> Run Collection
            </button>
          </Tooltip>
          <Tooltip text={taskButtonTooltip}>
            <button
              onClick={() => {
                if (onSwitchToLogs) onSwitchToLogs();
                triggerMutation.mutate('train');
              }}
              disabled={triggerMutation.isPending || isTaskRunning}
              className='btn-primary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
              type='button'
            >
              <RefreshCw size={16} /> Run Training
            </button>
          </Tooltip>
          <Tooltip text={taskButtonTooltip}>
            <button
              onClick={() => {
                if (onSwitchToLogs) onSwitchToLogs();
                triggerMutation.mutate('betting');
              }}
              disabled={triggerMutation.isPending || isTaskRunning}
              className='btn-primary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
              type='button'
            >
              <TrendingUp size={16} /> Place Bets
            </button>
          </Tooltip>
          <Tooltip
            text={
              taskButtonTooltip ||
              'Run collection, training, and betting in sequence'
            }
          >
            <button
              onClick={triggerFullRunWithWorkers}
              disabled={triggerMutation.isPending || isTaskRunning}
              className='btn-primary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
              type='button'
            >
              <Play size={16} /> Full Run
            </button>
          </Tooltip>
          <Tooltip text='Start daemon mode to run full cycles continuously'>
            <button
              onClick={() => {
                if (onSwitchToLogs) onSwitchToLogs();
                startDaemonMutation.mutate();
              }}
              disabled={startDaemonMutation.isPending || status?.running}
              className='btn-primary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
              type='button'
            >
              <Play size={16} /> Run Daemon
            </button>
          </Tooltip>
          <Tooltip text={stopButtonTooltip}>
            <button
              onClick={() => stopMutation.mutate()}
              disabled={!isTaskRunning || stopMutation.isPending}
              className='btn-danger ml-auto flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
              type='button'
            >
              <Square size={16} /> Stop
            </button>
          </Tooltip>
        </div>
      </div>

      {/* Scraper Workers Configuration */}
      <div className='card'>
        <div className='mb-4 flex items-center gap-2'>
          <Settings size={18} className='text-slate-400' />
          <h3 className='text-lg font-semibold'>Scraper Performance</h3>
        </div>
        <div className='space-y-4'>
          <p className='text-sm text-slate-400'>
            Configure parallel workers for data collection. Higher values =
            faster collection but more resource usage.
          </p>
          <div className='grid grid-cols-1 gap-4 md:grid-cols-3'>
            <div>
              <label className='mb-2 block text-sm text-slate-300'>
                League Workers (Betano)
                <Tooltip text='Number of leagues scraped in parallel for Betano (HTTP-based)'>
                  <span className='ml-1 cursor-help text-slate-500'>(?)</span>
                </Tooltip>
              </label>
              <input
                type='number'
                min={1}
                max={20}
                value={effectiveWorkersLeagues}
                onChange={(e) => setWorkersLeagues(Number(e.target.value))}
                className='w-full rounded-lg border border-slate-600 bg-slate-700/50 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none'
              />
            </div>
            <div>
              <label className='mb-2 block text-sm text-slate-300'>
                League Workers (FlashScore)
                <Tooltip text='Number of leagues scraped in parallel for FlashScore (browser-based, uses more resources)'>
                  <span className='ml-1 cursor-help text-slate-500'>(?)</span>
                </Tooltip>
              </label>
              <input
                type='number'
                min={1}
                max={10}
                value={effectiveWorkersPlaywright}
                onChange={(e) => setWorkersPlaywright(Number(e.target.value))}
                className='w-full rounded-lg border border-slate-600 bg-slate-700/50 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none'
              />
            </div>
            <div>
              <label className='mb-2 block text-sm text-slate-300'>
                Odds Workers
                <Tooltip text='Number of odds fetched in parallel per league'>
                  <span className='ml-1 cursor-help text-slate-500'>(?)</span>
                </Tooltip>
              </label>
              <input
                type='number'
                min={1}
                max={50}
                value={effectiveWorkersOdds}
                onChange={(e) => setWorkersOdds(Number(e.target.value))}
                className='w-full rounded-lg border border-slate-600 bg-slate-700/50 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none'
              />
            </div>
          </div>
          <button
            onClick={() =>
              updateScraperWorkersMutation.mutate({
                max_workers_leagues: effectiveWorkersLeagues,
                max_workers_odds: effectiveWorkersOdds,
                max_workers_leagues_playwright: effectiveWorkersPlaywright,
              })
            }
            disabled={updateScraperWorkersMutation.isPending}
            className='btn-secondary text-sm disabled:opacity-50'
            type='button'
          >
            Save as Default
          </button>
        </div>
      </div>

      {/* Configuration Panel */}
      <div className='card'>
        <h3 className='mb-4 text-lg font-semibold'>Fake Money Configuration</h3>
        {fakeMoneyConfig && (
          <div className='space-y-4'>
            <div className='flex items-center justify-between'>
              <label className='text-sm text-slate-300'>
                Auto-bet after training
              </label>
              <button
                onClick={() =>
                  updateFakeMoneyMutation.mutate({
                    auto_bet_after_training:
                      !fakeMoneyConfig.auto_bet_after_training,
                  })
                }
                disabled={updateFakeMoneyMutation.isPending}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  fakeMoneyConfig.auto_bet_after_training
                    ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                    : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                } disabled:opacity-50`}
                type='button'
              >
                {fakeMoneyConfig.auto_bet_after_training
                  ? 'Enabled'
                  : 'Disabled'}
              </button>
            </div>
            <div className='grid grid-cols-2 gap-4 text-sm'>
              <div>
                <p className='mb-1 text-slate-400'>Starting Balance</p>
                <p className='font-mono'>
                  ${fakeMoneyConfig.starting_balance?.toLocaleString() ?? '0'}
                </p>
              </div>
              <div>
                <p className='mb-1 text-slate-400'>Bet Sizing Strategy</p>
                <p className='capitalize'>
                  {fakeMoneyConfig.bet_sizing_strategy ?? 'fixed'}
                </p>
              </div>
              {fakeMoneyConfig.bet_sizing_strategy === 'fixed' && (
                <div>
                  <p className='mb-1 text-slate-400'>Fixed Stake</p>
                  <p className='font-mono'>
                    ${fakeMoneyConfig.fixed_stake ?? '0'}
                  </p>
                </div>
              )}
              {fakeMoneyConfig.bet_sizing_strategy === 'percentage' && (
                <div>
                  <p className='mb-1 text-slate-400'>Percentage Stake</p>
                  <p className='font-mono'>
                    {((fakeMoneyConfig.percentage_stake ?? 0) * 100).toFixed(1)}
                    %
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
