import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, Square, RefreshCw, TrendingUp, Settings, Zap, Wallet, ChevronDown } from 'lucide-react';
import { Tooltip } from '../Tooltip';
import type { createApi } from '../../api/api';
import type {
  ToastType,
  AutomationStatus,
  FakeMoneyConfig,
  ScraperWorkersConfig,
  TradingStatus,
} from '../../types';

interface AutomationTabProps {
  api: ReturnType<typeof createApi>;
  showToast: (message: string, type?: ToastType, duration?: number) => void;
  onSwitchToLogs?: () => void;
}

type Domain = 'betting' | 'trading';

/**
 * Automation tab component - displays automation controls and configuration
 * Unified interface for both betting and trading automation
 */
const AUTOMATION_DOMAIN_KEY = 'arbihawk_automation_domain';

export function AutomationTab({
  api,
  showToast,
  onSwitchToLogs,
}: AutomationTabProps) {
  const queryClient = useQueryClient();
  const [selectedDomain, setSelectedDomain] = useState<Domain>(() => {
    const saved = localStorage.getItem(AUTOMATION_DOMAIN_KEY);
    return (saved === 'betting' || saved === 'trading') ? saved : 'betting';
  });
  const [bettingMenuOpen, setBettingMenuOpen] = useState(false);
  const [tradingMenuOpen, setTradingMenuOpen] = useState(false);
  const bettingMenuRef = useRef<HTMLDivElement>(null);
  const tradingMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(AUTOMATION_DOMAIN_KEY, selectedDomain);
  }, [selectedDomain]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (bettingMenuRef.current && !bettingMenuRef.current.contains(event.target as Node)) {
        setBettingMenuOpen(false);
      }
      if (tradingMenuRef.current && !tradingMenuRef.current.contains(event.target as Node)) {
        setTradingMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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

  const { data: tradingStatus } = useQuery<TradingStatus>({
    queryKey: ['trading-status'],
    queryFn: () => api.getTradingStatus(),
    refetchInterval: 30000,
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
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ['status'] });
      showToast('Stop signal sent', 'success');
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

  // Trading automation mutations
  const tradingCollectionMutation = useMutation({
    mutationFn: api.triggerTradingCollection,
    onSuccess: () => {
      if (onSwitchToLogs) onSwitchToLogs();
      void queryClient.invalidateQueries({ queryKey: ['trading-status'] });
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to trigger trading collection', 'error');
    },
  });

  const tradingTrainingMutation = useMutation({
    mutationFn: api.triggerTradingTraining,
    onSuccess: () => {
      if (onSwitchToLogs) onSwitchToLogs();
      void queryClient.invalidateQueries({ queryKey: ['trading-status'] });
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to trigger trading training', 'error');
    },
  });

  const tradingCycleMutation = useMutation({
    mutationFn: api.triggerTradingCycle,
    onSuccess: () => {
      if (onSwitchToLogs) onSwitchToLogs();
      void queryClient.invalidateQueries({ queryKey: ['trading-status'] });
      void queryClient.invalidateQueries({ queryKey: ['trading-portfolio'] });
      void queryClient.invalidateQueries({ queryKey: ['trading-positions'] });
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to trigger trading cycle', 'error');
    },
  });

  const fullTradingCycleMutation = useMutation({
    mutationFn: api.triggerFullTradingCycle,
    onSuccess: () => {
      if (onSwitchToLogs) onSwitchToLogs();
      void queryClient.invalidateQueries({ queryKey: ['trading-status'] });
      void queryClient.invalidateQueries({ queryKey: ['trading-portfolio'] });
      void queryClient.invalidateQueries({ queryKey: ['trading-positions'] });
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to trigger full trading cycle', 'error');
    },
  });

  const startTradingDaemonMutation = useMutation({
    mutationFn: () => api.startTradingDaemon(3600), // 1 hour default
    onSuccess: () => {
      if (onSwitchToLogs) onSwitchToLogs();
      showToast('Trading daemon started', 'success');
      void queryClient.invalidateQueries({ queryKey: ['status'] });
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to start trading daemon', 'error');
    },
  });

  const stopTradingDaemonMutation = useMutation({
    mutationFn: api.stopTradingDaemon,
    onSuccess: async () => {
      await Promise.all([
        queryClient.refetchQueries({ queryKey: ['status'] }),
        queryClient.refetchQueries({ queryKey: ['trading-status'] }),
      ]);
      showToast('Stop signal sent', 'success');
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to stop trading automation', 'error');
    },
  });

  const initializePortfolioMutation = useMutation({
    mutationFn: api.initializeTradingPortfolio,
    onSuccess: () => {
      showToast('Portfolio initialized', 'success');
      void queryClient.invalidateQueries({ queryKey: ['trading-portfolio'] });
    },
    onError: (error: Error) => {
      showToast(error.message ?? 'Failed to initialize portfolio', 'error');
    },
  });

  // Check if betting task is running (betting tasks don't start with "trading_")
  const isBettingTaskRunning = !!(status?.current_task && !status.current_task.startsWith('trading_'));
  // Check if trading task is running (trading tasks start with "trading_")
  const isTradingTaskRunning = tradingStatus?.current_task ? true : false;
  // Check if betting daemon is running
  const isBettingDaemonRunning = status?.running || false;
  // Check if trading daemon is running
  const isTradingDaemonRunning = status?.trading_daemon_running || false;
  
  // For betting domain: stop button enabled if task OR daemon is running
  const isBettingRunning = isBettingTaskRunning || isBettingDaemonRunning;
  // For trading domain: stop button enabled if task OR daemon is running
  const isTradingRunning = isTradingTaskRunning || isTradingDaemonRunning;
  
  const bettingTaskButtonTooltip = isBettingTaskRunning || isBettingDaemonRunning
    ? 'You can only run one task at a time for betting'
    : '';
  const tradingTaskButtonTooltip = isTradingTaskRunning || isTradingDaemonRunning
    ? 'You can only run one task at a time for trading'
    : '';
  const bettingStopButtonTooltip = !isBettingRunning
    ? 'No betting task or daemon is currently running'
    : '';
  const tradingStopButtonTooltip = !isTradingRunning
    ? 'No trading task or daemon is currently running'
    : '';

  return (
    <div className='space-y-6'>
      {/* Domain Selector - Prominent at top */}
      <div className='flex items-center gap-4'>
        <button
          onClick={() => setSelectedDomain('betting')}
          className={`flex-1 px-6 py-3 text-sm font-semibold rounded-lg transition-all ${selectedDomain === 'betting'
            ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/20'
            : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50 hover:text-slate-300'
            }`}
          type='button'
        >
          Betting Automation
        </button>
        <button
          onClick={() => setSelectedDomain('trading')}
          className={`flex-1 px-6 py-3 text-sm font-semibold rounded-lg transition-all ${selectedDomain === 'trading'
            ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20'
            : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50 hover:text-slate-300'
            }`}
          type='button'
        >
          Trading Automation
        </button>
      </div>

      <div className='card relative'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='text-lg font-semibold'>Automation Control</h3>
          <div
            className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm ${selectedDomain === 'betting'
              ? status?.running
                ? 'bg-sky-500/20 text-sky-400'
                : 'bg-slate-700 text-slate-400'
              : tradingStatus?.enabled
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-slate-700 text-slate-400'
              }`}
          >
            {selectedDomain === 'betting'
              ? status?.running
                ? 'Running'
                : 'Stopped'
              : tradingStatus?.enabled
                ? 'Enabled'
                : 'Disabled'}
          </div>
        </div>

        {/* Status metrics - domain-specific */}
        {selectedDomain === 'betting' ? (
          <div className='mb-6 grid grid-cols-1 gap-4 md:grid-cols-4'>
            <div className='rounded-lg bg-slate-800/50 p-4'>
              <p className='text-sm text-slate-400'>Current Task</p>
              <p className='font-medium'>
                {/* Only show betting tasks (tasks that don't start with trading_) */}
                {status?.current_task && !status.current_task.startsWith('trading_')
                  ? status.stopping 
                    ? `${status.current_task} (Stopping...)`
                    : status.current_task
                  : 'None'}
              </p>
            </div>
            <div className='rounded-lg bg-slate-800/50 p-4'>
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
            <div className='rounded-lg bg-slate-800/50 p-4'>
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
            <div className='rounded-lg bg-slate-800/50 p-4'>
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
        ) : (
          <div className='mb-6 grid grid-cols-1 gap-4 md:grid-cols-3'>
            <div className='rounded-lg bg-slate-800/50 p-4'>
              <p className='text-sm text-slate-400'>Last Data Collection</p>
              <p className='font-mono text-sm font-medium'>
                {tradingStatus?.last_collection
                  ? new Date(tradingStatus.last_collection).toLocaleString()
                  : 'Never'}
              </p>
              {tradingStatus?.last_collection_duration_seconds != null && (
                <p className='mt-1 text-xs text-slate-500'>
                  Duration:{' '}
                  {tradingStatus.last_collection_duration_seconds >= 60
                    ? `${(tradingStatus.last_collection_duration_seconds / 60).toFixed(1)} min`
                    : `${tradingStatus.last_collection_duration_seconds.toFixed(1)}s`}
                </p>
              )}
            </div>
            <div className='rounded-lg bg-slate-800/50 p-4'>
              <Tooltip text='API key configuration status. Green = configured, Red = missing'>
                <div className='cursor-help'>
                  <p className='text-sm text-slate-400 flex items-center gap-1'>
                    API Keys Status
                    <span className='text-slate-500 text-xs'>(?)</span>
                  </p>
                  <div className='mt-1 flex gap-2 text-xs'>
                    <span className={`${tradingStatus?.api_keys_configured?.alpha_vantage ? 'text-emerald-400' : 'text-red-400'}`}>
                      {tradingStatus?.api_keys_configured?.alpha_vantage ? '✓' : '✗'} Stocks
                    </span>
                    <span className='text-slate-500'>/</span>
                    <span className={`${tradingStatus?.api_keys_configured?.coingecko ? 'text-emerald-400' : 'text-red-400'}`}>
                      {tradingStatus?.api_keys_configured?.coingecko ? '✓' : '✗'} Crypto
                    </span>
                  </div>
                </div>
              </Tooltip>
            </div>
            <div className='rounded-lg bg-slate-800/50 p-4'>
              <p className='text-sm text-slate-400'>Watchlist</p>
              <p className='font-mono text-sm font-medium'>
                {tradingStatus?.watchlist
                  ? `${tradingStatus.watchlist.stocks?.length ?? 0} stocks, ${tradingStatus.watchlist.crypto?.length ?? 0} crypto`
                  : 'Not configured'}
              </p>
            </div>
          </div>
        )}

        {/* Domain-specific controls */}
        {selectedDomain === 'betting' ? (
          <div className='space-y-3' ref={bettingMenuRef}>
            <div className='flex items-center justify-between gap-3'>
              <div className='flex-1'>
                <button
                  onClick={() => setBettingMenuOpen(!bettingMenuOpen)}
                  disabled={triggerMutation.isPending || isBettingTaskRunning}
                  className='btn-primary w-full flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
                  type='button'
                >
                  <Play size={16} /> Actions
                  <ChevronDown size={16} className={`transition-transform ${bettingMenuOpen ? 'rotate-180' : ''}`} />
                </button>
              </div>
              <Tooltip text={bettingStopButtonTooltip}>
                <button
                  onClick={() => stopMutation.mutate()}
                  disabled={!isBettingRunning || stopMutation.isPending}
                  className='btn-danger flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
                  type='button'
                >
                  {stopMutation.isPending ? (
                    <>
                      <RefreshCw size={16} className='animate-spin' /> Stopping...
                    </>
                  ) : (
                    <>
                      <Square size={16} /> Stop
                    </>
                  )}
                </button>
              </Tooltip>
            </div>
            {bettingMenuOpen && (
              <div className='rounded-lg border border-slate-700 bg-slate-800/50 p-1'>
                <Tooltip text={bettingTaskButtonTooltip}>
                  <button
                    onClick={() => {
                      triggerCollectionWithWorkers();
                      setBettingMenuOpen(false);
                    }}
                    disabled={triggerMutation.isPending || isBettingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <Play size={16} /> Run Collection
                  </button>
                </Tooltip>
                <Tooltip text={bettingTaskButtonTooltip}>
                  <button
                    onClick={() => {
                      if (onSwitchToLogs) onSwitchToLogs();
                      triggerMutation.mutate('train');
                      setBettingMenuOpen(false);
                    }}
                    disabled={triggerMutation.isPending || isBettingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <RefreshCw size={16} /> Run Training
                  </button>
                </Tooltip>
                <Tooltip text={bettingTaskButtonTooltip}>
                  <button
                    onClick={() => {
                      if (onSwitchToLogs) onSwitchToLogs();
                      triggerMutation.mutate('betting');
                      setBettingMenuOpen(false);
                    }}
                    disabled={triggerMutation.isPending || isBettingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <TrendingUp size={16} /> Place Bets
                  </button>
                </Tooltip>
                <div className='my-1 border-t border-slate-700' />
                <Tooltip text={bettingTaskButtonTooltip || 'Run collection, training, and betting in sequence'} className='w-full'>
                  <button
                    onClick={() => {
                      triggerFullRunWithWorkers();
                      setBettingMenuOpen(false);
                    }}
                    disabled={triggerMutation.isPending || isBettingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <Play size={16} /> Full Run
                  </button>
                </Tooltip>
                <Tooltip text='Start daemon mode to run full cycles continuously' className='w-full'>
                  <button
                    onClick={() => {
                      if (onSwitchToLogs) onSwitchToLogs();
                      startDaemonMutation.mutate();
                      setBettingMenuOpen(false);
                    }}
                    disabled={startDaemonMutation.isPending || isBettingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <Play size={16} /> Run Daemon
                  </button>
                </Tooltip>
              </div>
            )}
          </div>
        ) : (
          <div className='space-y-3' ref={tradingMenuRef}>
            <div className='flex items-center justify-between gap-3'>
              <div className='flex-1'>
                <button
                  onClick={() => setTradingMenuOpen(!tradingMenuOpen)}
                  disabled={!tradingStatus?.enabled}
                  className='btn-primary w-full flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
                  type='button'
                >
                  <Play size={16} /> Actions
                  <ChevronDown size={16} className={`transition-transform ${tradingMenuOpen ? 'rotate-180' : ''}`} />
                </button>
              </div>
              <Tooltip text={tradingStopButtonTooltip}>
                <button
                  onClick={() => stopTradingDaemonMutation.mutate()}
                  disabled={!isTradingRunning || stopTradingDaemonMutation.isPending}
                  className='btn-danger flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50'
                  type='button'
                >
                  {stopTradingDaemonMutation.isPending ? (
                    <>
                      <RefreshCw size={16} className='animate-spin' /> Stopping...
                    </>
                  ) : (
                    <>
                      <Square size={16} /> Stop
                    </>
                  )}
                </button>
              </Tooltip>
            </div>
            {tradingMenuOpen && (
              <div className='rounded-lg border border-slate-700 bg-slate-800/50 p-1'>
                <Tooltip text={tradingStatus?.enabled ? tradingTaskButtonTooltip : 'Trading is disabled in configuration'}>
                  <button
                    onClick={() => {
                      tradingCollectionMutation.mutate();
                      setTradingMenuOpen(false);
                    }}
                    disabled={!tradingStatus?.enabled || tradingCollectionMutation.isPending || isTradingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <RefreshCw size={16} /> Collect Data
                  </button>
                </Tooltip>
                <Tooltip text={tradingStatus?.enabled ? tradingTaskButtonTooltip : 'Trading is disabled in configuration'}>
                  <button
                    onClick={() => {
                      tradingTrainingMutation.mutate();
                      setTradingMenuOpen(false);
                    }}
                    disabled={!tradingStatus?.enabled || tradingTrainingMutation.isPending || isTradingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <Zap size={16} /> Train Models
                  </button>
                </Tooltip>
                <Tooltip text={tradingStatus?.enabled ? tradingTaskButtonTooltip : 'Trading is disabled in configuration'}>
                  <button
                    onClick={() => {
                      if (onSwitchToLogs) onSwitchToLogs();
                      tradingCycleMutation.mutate();
                      setTradingMenuOpen(false);
                    }}
                    disabled={!tradingStatus?.enabled || tradingCycleMutation.isPending || isTradingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <Play size={16} /> Run Trading Cycle
                  </button>
                </Tooltip>
                <div className='my-1 border-t border-slate-700' />
                <Tooltip text={tradingStatus?.enabled ? (tradingTaskButtonTooltip || 'Run collection, training, and cycle in sequence') : 'Trading is disabled in configuration'} className='w-full'>
                  <button
                    onClick={() => {
                      if (onSwitchToLogs) onSwitchToLogs();
                      fullTradingCycleMutation.mutate();
                      setTradingMenuOpen(false);
                    }}
                    disabled={!tradingStatus?.enabled || fullTradingCycleMutation.isPending || isTradingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <Play size={16} /> Full Run
                  </button>
                </Tooltip>
                <Tooltip text={tradingStatus?.enabled ? 'Start daemon mode to run full cycles continuously (every hour)' : 'Trading is disabled in configuration'} className='w-full'>
                  <button
                    onClick={() => {
                      if (onSwitchToLogs) onSwitchToLogs();
                      startTradingDaemonMutation.mutate();
                      setTradingMenuOpen(false);
                    }}
                    disabled={!tradingStatus?.enabled || startTradingDaemonMutation.isPending || isTradingRunning}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <Play size={16} /> Start Daemon
                  </button>
                </Tooltip>
                <div className='my-1 border-t border-slate-700' />
                <Tooltip text='Initialize portfolio with starting balance' className='w-full'>
                  <button
                    onClick={() => {
                      initializePortfolioMutation.mutate(undefined);
                      setTradingMenuOpen(false);
                    }}
                    disabled={initializePortfolioMutation.isPending}
                    className='w-full flex items-center gap-2 rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'
                    type='button'
                  >
                    <Wallet size={16} /> Initialize Portfolio
                  </button>
                </Tooltip>
              </div>
            )}
            {!tradingStatus?.enabled && (
              <p className='text-sm text-slate-500'>
                Enable trading in config.json to use trading automation
              </p>
            )}
          </div>
        )}
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
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${fakeMoneyConfig.auto_bet_after_training
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
