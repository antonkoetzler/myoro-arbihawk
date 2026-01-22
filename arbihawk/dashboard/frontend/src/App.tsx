import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useToast } from './hooks/useToast';
import { useWebSocketLogs } from './hooks/useWebSocketLogs';
import { createApi } from './api/api';
import { TAB_QUERIES } from './utils/constants';
import { SystemTab } from './components/tabs/SystemTab';
import { BetsTab } from './components/tabs/BetsTab';
import { BettingTab } from './components/tabs/BettingTab';
import { AutomationTab } from './components/tabs/AutomationTab';
import { ModelsTab } from './components/tabs/ModelsTab';
import { LogsTab } from './components/tabs/LogsTab';
import type { HealthResponse, Bankroll } from './types';

type Tab = 'system' | 'bets' | 'betting' | 'automation' | 'models' | 'logs';

/**
 * Main App component - orchestrates the dashboard
 */
function App() {
  const [activeTab, setActiveTab] = useState<Tab>('system');
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

  // Invalidate and refetch queries for the new tab when switching
  useEffect(() => {
    const queriesToRefetch = TAB_QUERIES[activeTab] ?? [];
    queriesToRefetch.forEach((key) => {
      void queryClient.invalidateQueries({ queryKey: [key] });
    });
  }, [activeTab, queryClient]);

  const tabs: Tab[] = [
    'system',
    'bets',
    'betting',
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
            <h1 className='bg-gradient-to-r from-sky-400 to-cyan-400 bg-clip-text text-3xl font-bold text-transparent'>
              Arbihawk Dashboard
            </h1>
            <p className='mt-1 text-slate-400'>Betting Prediction System</p>
          </div>
          <div className='flex items-center gap-4'>
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
                ? 'bg-sky-500 text-white'
                : 'text-slate-400 hover:bg-slate-700/50 hover:text-white'
            }`}
            type='button'
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* Tab Content */}
      {activeTab === 'system' && <SystemTab api={api} />}
      {activeTab === 'bets' && <BetsTab api={api} bankroll={bankroll} />}
      {activeTab === 'betting' && <BettingTab api={api} />}
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
    </div>
  );
}

export default App;
