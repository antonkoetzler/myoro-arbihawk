import { useState, useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useToast } from './hooks/useToast';
import { useWebSocketLogs } from './hooks/useWebSocketLogs';
import { createApi } from './api/api';
import { TAB_QUERIES } from './utils/constants';
import { ErrorBoundary } from './components/ErrorBoundary';
import { SystemTab } from './components/tabs/SystemTab';
import { BettingTab } from './components/tabs/BettingTab';
import { AutomationTab } from './components/tabs/AutomationTab';
import { ModelsTab } from './components/tabs/ModelsTab';
import { LogsTab } from './components/tabs/LogsTab';
import { TradingTab } from './components/tabs/TradingTab';
import { PolymarketTab } from './components/tabs/PolymarketTab';
import type { HealthResponse, Bankroll } from './types';

type Tab = 'system' | 'betting' | 'trading' | 'polymarket' | 'automation' | 'models' | 'logs';

/**
 * Main App component - orchestrates the dashboard
 */
const TAB_STORAGE_KEY = 'arbihawk_active_tab';

function App() {
  // Load active tab from localStorage on mount
  const [activeTab, setActiveTab] = useState<Tab>(() => {
    const saved = localStorage.getItem(TAB_STORAGE_KEY);
    if (saved && ['system', 'bets', 'betting', 'trading', 'polymarket', 'automation', 'models', 'logs'].includes(saved)) {
      return saved as Tab;
    }
    return 'system';
  });
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const showToast = useToast();
  const api = createApi(showToast);

  // WebSocket logs with clear function
  const {
    logs: wsLogs,
    connected: wsConnected,
    clearLogs,
  } = useWebSocketLogs();

  // Helper to determine if a query should be enabled and polling
  const shouldPoll = (queryKey: string): boolean => {
    return TAB_QUERIES[activeTab]?.includes(queryKey) ?? false;
  };

  // Queries with tab-based polling
  const { data: health } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: shouldPoll('health') ? 30000 : false,
    retry: false,
  });
  const { data: bankroll } = useQuery<Bankroll>({
    queryKey: ['bankroll'],
    queryFn: api.getBankroll,
    refetchInterval: shouldPoll('bankroll') ? 30000 : false,
    retry: false,
  });

  const { data: environment } = useQuery({
    queryKey: ['environment'],
    queryFn: api.getEnvironment,
    refetchInterval: false,
    retry: false,
  });

  // Save active tab to localStorage when it changes
  useEffect(() => {
    localStorage.setItem(TAB_STORAGE_KEY, activeTab);
  }, [activeTab]);

  // Invalidate and refetch queries for the new tab when switching
  useEffect(() => {
    const queriesToRefetch = TAB_QUERIES[activeTab] ?? [];
    queriesToRefetch.forEach((key) => {
      void queryClient.invalidateQueries({ queryKey: [key] });
    });
  }, [activeTab, queryClient]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const tabs: Tab[] = [
    'system',
    'betting',
    'trading',
    'polymarket',
    'automation',
    'models',
    'logs',
  ];

  return (
    <div className='min-h-screen p-6'>
      {/* Header */}
      <header className='mb-8'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-3xl font-bold text-transparent'>
              Arbihawk Dashboard
            </h1>
            <p className='mt-1 text-slate-400'>ML-Powered Prediction & Trading Platform</p>
          </div>
          <div className='flex items-center gap-4'>
            {/* Environment Selector */}
            {environment && (
              <div className='relative' ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                    environment.environment === 'debug'
                      ? 'border-amber-500/50 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20'
                      : 'border-blue-500/50 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20'
                  }`}
                >
                  <span>{environment.environment === 'debug' ? 'Debug' : 'Production'}</span>
                  <svg
                    className={`h-3 w-3 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`}
                    fill='none'
                    stroke='currentColor'
                    viewBox='0 0 24 24'
                  >
                    <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M19 9l-7 7-7-7' />
                  </svg>
                </button>
                {dropdownOpen && (
                  <div className='absolute right-0 top-full z-50 mt-1 min-w-[120px] rounded-lg border border-slate-700/50 bg-slate-800/95 shadow-xl backdrop-blur-sm'>
                    <button
                      onClick={async () => {
                        if (environment.environment !== 'debug') {
                          try {
                            await api.updateEnvironment('debug');
                            showToast(
                              'Environment switched to debug. Page will refresh.',
                              'success'
                            );
                            setTimeout(() => {
                              window.location.reload();
                            }, 1000);
                          } catch (err) {
                            // Error already shown by API
                          }
                        }
                        setDropdownOpen(false);
                      }}
                      className={`w-full px-3 py-2 text-left text-xs font-medium transition-colors first:rounded-t-lg last:rounded-b-lg ${
                        environment.environment === 'debug'
                          ? 'bg-amber-500/20 text-amber-400'
                          : 'text-slate-300 hover:bg-slate-700/50'
                      }`}
                    >
                      Debug
                    </button>
                    <button
                      onClick={async () => {
                        if (environment.environment !== 'production') {
                          try {
                            await api.updateEnvironment('production');
                            showToast(
                              'Environment switched to production. Page will refresh.',
                              'success'
                            );
                            setTimeout(() => {
                              window.location.reload();
                            }, 1000);
                          } catch (err) {
                            // Error already shown by API
                          }
                        }
                        setDropdownOpen(false);
                      }}
                      className={`w-full px-3 py-2 text-left text-xs font-medium transition-colors first:rounded-t-lg last:rounded-b-lg ${
                        environment.environment === 'production'
                          ? 'bg-blue-500/20 text-blue-400'
                          : 'text-slate-300 hover:bg-slate-700/50'
                      }`}
                    >
                      Production
                    </button>
                  </div>
                )}
              </div>
            )}
            {/* Health Status */}
            <div
              className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm ${
                health?.status === 'healthy'
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-red-500/20 text-red-400'
              }`}
            >
              <div
                className={`h-2 w-2 rounded-full ${
                  health?.status === 'healthy' ? 'bg-emerald-400' : 'bg-red-400'
                } animate-pulse`}
              />
              {health?.status === 'healthy'
                ? 'Healthy'
                : health?.status
                  ? health.status.charAt(0).toUpperCase() +
                    health.status.slice(1)
                  : 'Unknown'}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className='mb-6 flex gap-2 border-b border-slate-700/50 pb-4'>
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`rounded-lg px-4 py-2 capitalize transition-all ${
              activeTab === tab
                ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20'
                : 'text-slate-400 hover:bg-slate-700/50 hover:text-white'
            }`}
            type='button'
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* Tab Content */}
      <ErrorBoundary>
        {activeTab === 'system' && <SystemTab api={api} showToast={showToast} />}
        {activeTab === 'betting' && <BettingTab api={api} bankroll={bankroll} />}
        {activeTab === 'trading' && <TradingTab api={api} />}
        {activeTab === 'polymarket' && <PolymarketTab api={api} />}
        {activeTab === 'automation' && (
          <AutomationTab 
            api={api} 
            showToast={showToast}
            onSwitchToLogs={() => setActiveTab('logs')}
          />
        )}
        {activeTab === 'models' && <ModelsTab api={api} />}
        {activeTab === 'logs' && (
          <LogsTab
            wsLogs={wsLogs}
            wsConnected={wsConnected}
            clearLogs={clearLogs}
          />
        )}
      </ErrorBoundary>
    </div>
  );
}

export default App;
