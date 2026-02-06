import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Activity, DollarSign, BarChart3, Clock } from 'lucide-react';
import type { ApiClient } from '../../types';

interface PolymarketStats {
  total_trades: number;
  executed_trades: number;
  total_pnl: number;
  total_expected_pnl: number;
  bankroll: number;
  available_bankroll: number;
  strategy_stats: Record<string, {
    name: string;
    total_pnl: number;
    trade_count: number;
    win_rate: number;
  }>;
  recent_trades: Array<{
    trade_id: string;
    strategy: string;
    market_title: string;
    trade_type: string;
    amount: number;
    expected_profit: number;
    timestamp: string;
    status: string;
  }>;
}

interface Props {
  api: ApiClient;
}

export function PolymarketTab({ api }: Props) {
  const [isRunning, setIsRunning] = useState(false);

  const { data: stats, refetch } = useQuery<PolymarketStats>({
    queryKey: ['polymarket-stats'],
    queryFn: api.getPolymarketStats,
    refetchInterval: 30000,
    retry: false,
  });

  const handleRunScan = async () => {
    setIsRunning(true);
    try {
      await api.runPolymarketScan();
      await refetch();
    } catch (err) {
      console.error('Scan failed:', err);
    } finally {
      setIsRunning(false);
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(val);
  };

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleString();
  };

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold text-white'>Polymarket Trading</h2>
          <p className='text-slate-400'>Multi-strategy prediction market trading</p>
        </div>
        <button
          onClick={handleRunScan}
          disabled={isRunning}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 font-medium transition-all ${
            isRunning
              ? 'cursor-not-allowed bg-slate-700 text-slate-400'
              : 'bg-emerald-500 text-white hover:bg-emerald-600'
          }`}
        >
          {isRunning ? (
            <>
              <div className='h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent' />
              Running...
            </>
          ) : (
            <>
              <Activity className='h-4 w-4' />
              Run Scan
            </>
          )}
        </button>
      </div>

      {/* Stats Grid */}
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
        <StatCard
          title='Total Trades'
          value={stats?.total_trades ?? 0}
          icon={<BarChart3 className='h-5 w-5 text-blue-400' />}
        />
        <StatCard
          title='Expected PnL'
          value={formatCurrency(stats?.total_expected_pnl ?? 0)}
          icon={<TrendingUp className='h-5 w-5 text-emerald-400' />}
          trend={stats?.total_expected_pnl && stats.total_expected_pnl > 0 ? 'positive' : 'neutral'}
        />
        <StatCard
          title='Bankroll'
          value={formatCurrency(stats?.bankroll ?? 100)}
          icon={<DollarSign className='h-5 w-5 text-amber-400' />}
        />
        <StatCard
          title='Available'
          value={formatCurrency(stats?.available_bankroll ?? 100)}
          icon={<Clock className='h-5 w-5 text-purple-400' />}
        />
      </div>

      {/* Strategy Performance */}
      <div className='rounded-xl border border-slate-700/50 bg-slate-800/50 p-6'>
        <h3 className='mb-4 text-lg font-semibold text-white'>Strategy Performance</h3>
        <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
          {stats?.strategy_stats ? (
            Object.entries(stats.strategy_stats).map(([name, stratStats]) => (
              <div
                key={name}
                className='rounded-lg border border-slate-700/50 bg-slate-900/50 p-4'
              >
                <div className='mb-2 text-sm font-medium text-slate-400'>{name}</div>
                <div className='text-2xl font-bold text-white'>{stratStats.trade_count}</div>
                <div className='text-xs text-slate-500'>trades</div>
                <div className={`mt-2 text-sm font-medium ${
                  stratStats.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {formatCurrency(stratStats.total_pnl)}
                </div>
              </div>
            ))
          ) : (
            <div className='col-span-full text-center text-slate-500'>
              No strategy data available
            </div>
          )}
        </div>
      </div>

      {/* Recent Trades */}
      <div className='rounded-xl border border-slate-700/50 bg-slate-800/50 p-6'>
        <h3 className='mb-4 text-lg font-semibold text-white'>Recent Trades</h3>
        <div className='overflow-x-auto'>
          <table className='w-full text-sm'>
            <thead>
              <tr className='border-b border-slate-700/50 text-left text-slate-400'>
                <th className='pb-3 font-medium'>Strategy</th>
                <th className='pb-3 font-medium'>Market</th>
                <th className='pb-3 font-medium'>Type</th>
                <th className='pb-3 font-medium'>Amount</th>
                <th className='pb-3 font-medium'>Expected Profit</th>
                <th className='pb-3 font-medium'>Time</th>
                <th className='pb-3 font-medium'>Status</th>
              </tr>
            </thead>
            <tbody className='divide-y divide-slate-700/30'>
              {stats?.recent_trades && stats.recent_trades.length > 0 ? (
                stats.recent_trades.map((trade) => (
                  <tr key={trade.trade_id} className='text-slate-300'>
                    <td className='py-3'>
                      <span className='rounded bg-slate-700/50 px-2 py-1 text-xs font-medium'>
                        {trade.strategy}
                      </span>
                    </td>
                    <td className='py-3 max-w-xs truncate' title={trade.market_title}>
                      {trade.market_title}
                    </td>
                    <td className='py-3 text-slate-400'>{trade.trade_type}</td>
                    <td className='py-3'>{formatCurrency(trade.amount)}</td>
                    <td className='py-3 text-emerald-400'>
                      +{formatCurrency(trade.expected_profit)}
                    </td>
                    <td className='py-3 text-slate-500'>{formatDate(trade.timestamp)}</td>
                    <td className='py-3'>
                      <span className={`rounded px-2 py-1 text-xs font-medium ${
                        trade.status === 'executed'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : trade.status === 'pending'
                          ? 'bg-amber-500/20 text-amber-400'
                          : 'bg-slate-700/50 text-slate-400'
                      }`}>
                        {trade.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className='py-8 text-center text-slate-500'>
                    No trades yet. Run a scan to start trading.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: 'positive' | 'negative' | 'neutral';
}

function StatCard({ title, value, icon, trend }: StatCardProps) {
  return (
    <div className='rounded-xl border border-slate-700/50 bg-slate-800/50 p-4'>
      <div className='flex items-center justify-between'>
        <span className='text-sm font-medium text-slate-400'>{title}</span>
        {icon}
      </div>
      <div className='mt-2 flex items-center gap-2'>
        <span className={`text-2xl font-bold ${
          trend === 'positive' ? 'text-emerald-400' :
          trend === 'negative' ? 'text-red-400' :
          'text-white'
        }`}>
          {value}
        </span>
        {trend === 'positive' && <TrendingUp className='h-4 w-4 text-emerald-400' />}
        {trend === 'negative' && <TrendingDown className='h-4 w-4 text-red-400' />}
      </div>
    </div>
  );
}
