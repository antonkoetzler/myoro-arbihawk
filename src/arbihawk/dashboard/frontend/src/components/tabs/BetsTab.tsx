import { useQuery } from '@tanstack/react-query';
import { Activity, TrendingUp, Database } from 'lucide-react';
import { StatCard } from '../StatCard';
import { EmptyState } from '../EmptyState';
import { formatPercent, formatMoney } from '../../utils/formatters';
import type { createApi } from '../../api/api';
import type { Bankroll, BetsResponse } from '../../types';

interface BetsTabProps {
  api: ReturnType<typeof createApi>;
  bankroll: Bankroll | undefined;
}

/**
 * Bets tab component - displays betting statistics and recent bets
 */
export function BetsTab({ api, bankroll }: BetsTabProps) {
  const { data: bets } = useQuery<BetsResponse>({
    queryKey: ['bets-recent'],
    queryFn: () => api.getBets({ per_page: 50 }),
    refetchInterval: 30000,
    retry: false,
  });

  // Determine win rate trend - neutral when no wins AND no losses
  const getWinRateTrend = (): 'up' | 'down' | null => {
    const wins = bankroll?.wins ?? 0;
    const losses = bankroll?.losses ?? 0;
    if (wins === 0 && losses === 0) return null; // Neutral
    return (bankroll?.win_rate ?? 0) > 0.5 ? 'up' : 'down';
  };

  return (
    <div className='space-y-6'>
      {/* Stats Grid */}
      <div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4'>
        <StatCard
          title='Balance'
          value={formatMoney(bankroll?.current_balance)}
          subtitle={`Started: ${formatMoney(bankroll?.starting_balance)}`}
          icon={TrendingUp}
          trend={
            bankroll && bankroll.profit > 0
              ? 'up'
              : bankroll && bankroll.profit < 0
                ? 'down'
                : null
          }
        />
        <StatCard
          title='ROI'
          value={formatPercent(bankroll?.roi)}
          subtitle={`Profit: ${formatMoney(bankroll?.profit)}`}
          icon={Activity}
          trend={
            bankroll && bankroll.roi > 0
              ? 'up'
              : bankroll && bankroll.roi < 0
                ? 'down'
                : null
          }
        />
        <StatCard
          title='Win Rate'
          value={formatPercent(bankroll?.win_rate)}
          subtitle={`${bankroll?.wins ?? 0}W / ${bankroll?.losses ?? 0}L`}
          icon={TrendingUp}
          trend={getWinRateTrend()}
        />
        <StatCard
          title='Total Bets'
          value={bankroll?.total_bets ?? 0}
          subtitle={`Pending: ${bankroll?.pending_bets ?? 0}`}
          icon={Database}
        />
      </div>

      {/* Recent Bets */}
      <div className='card'>
        <h3 className='mb-4 text-lg font-semibold'>Recent Bets</h3>
        <div className='max-h-64 space-y-2 overflow-y-auto'>
          {bets?.bets && bets.bets.length > 0 ? (
            bets.bets.slice(0, 10).map((bet, i) => (
              <div
                key={i}
                className='flex items-center justify-between border-b border-slate-700/50 py-2 last:border-0'
              >
                <div>
                  <p className='text-sm font-medium'>
                    {bet.market_name ?? 'Unknown'}
                  </p>
                  <p className='text-xs text-slate-400'>{bet.outcome_name}</p>
                  {bet.model_market && (
                    <p className='mt-1 text-xs text-slate-500'>
                      Model: {bet.model_market}
                    </p>
                  )}
                </div>
                <div className='text-right'>
                  <p
                    className={`font-mono text-sm ${bet.result === 'win' ? 'text-emerald-400' : bet.result === 'loss' ? 'text-red-400' : 'text-slate-400'}`}
                  >
                    {bet.result === 'win'
                      ? `+$${bet.payout?.toFixed(2)}`
                      : bet.result === 'loss'
                        ? `-$${bet.stake?.toFixed(2)}`
                        : 'Pending'}
                  </p>
                  <p className='text-xs text-slate-500'>{bet.odds}x</p>
                </div>
              </div>
            ))
          ) : (
            <EmptyState
              icon={TrendingUp}
              title='No Bets Yet'
              description='Place bets to see them here'
            />
          )}
        </div>
      </div>

      {/* Per-Model Performance */}
      {bankroll?.by_model && Object.keys(bankroll.by_model).length > 0 && (
        <div className='card'>
          <h3 className='mb-4 text-lg font-semibold'>Performance by Model</h3>
          <div className='grid grid-cols-1 gap-4 md:grid-cols-3'>
            {Object.entries(bankroll.by_model).map(([market, stats]) => (
              <div key={market} className='rounded-lg bg-slate-700/30 p-4'>
                <p className='mb-2 font-medium capitalize'>{market}</p>
                <div className='space-y-1 text-sm'>
                  <p className='text-slate-400'>
                    Bets:{' '}
                    <span className='text-slate-300'>{stats.total_bets}</span>
                  </p>
                  <p className='text-slate-400'>
                    Win Rate:{' '}
                    <span className='text-slate-300'>
                      {formatPercent(stats.win_rate)}
                    </span>
                  </p>
                  <p className='text-slate-400'>
                    ROI:{' '}
                    <span
                      className={
                        stats.roi > 0
                          ? 'text-emerald-400'
                          : stats.roi < 0
                            ? 'text-red-400'
                            : 'text-slate-300'
                      }
                    >
                      {formatPercent(stats.roi)}
                    </span>
                  </p>
                  <p className='text-slate-400'>
                    Profit:{' '}
                    <span
                      className={
                        stats.profit > 0
                          ? 'text-emerald-400'
                          : stats.profit < 0
                            ? 'text-red-400'
                            : 'text-slate-300'
                      }
                    >
                      {formatMoney(stats.profit)}
                    </span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
