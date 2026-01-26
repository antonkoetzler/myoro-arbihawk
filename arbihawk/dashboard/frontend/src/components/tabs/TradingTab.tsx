import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Wallet, TrendingUp, TrendingDown, Activity, Target,
  DollarSign, BarChart3, Zap, Plus, X
} from 'lucide-react';
import type { createApi } from '../../api/api';
import { StatCard } from '../StatCard';
import { EmptyState } from '../EmptyState';

interface TradingTabProps {
  api: ReturnType<typeof createApi>;
}

/**
 * Trading tab component - displays trading portfolio, positions, signals, and performance
 */
export function TradingTab({ api }: TradingTabProps) {
  // Fetch trading status
  const { data: status } = useQuery({
    queryKey: ['trading-status'],
    queryFn: () => api.getTradingStatus(),
    refetchInterval: 30000,
    retry: false,
  });

  // Fetch portfolio
  const { data: portfolio } = useQuery({
    queryKey: ['trading-portfolio'],
    queryFn: () => api.getTradingPortfolio(),
    refetchInterval: 10000,
    retry: false,
  });

  // Fetch positions
  const { data: positionsData } = useQuery({
    queryKey: ['trading-positions'],
    queryFn: () => api.getTradingPositions(),
    refetchInterval: 10000,
    retry: false,
  });

  // Fetch trades
  const { data: tradesData } = useQuery({
    queryKey: ['trading-trades'],
    queryFn: () => api.getTradingTrades(20),
    refetchInterval: 30000,
    retry: false,
  });

  // Fetch signals
  const { data: signalsData } = useQuery({
    queryKey: ['trading-signals'],
    queryFn: () => api.getTradingSignals(10),
    refetchInterval: 30000,
    retry: false,
  });

  // Fetch performance
  const { data: performance } = useQuery({
    queryKey: ['trading-performance'],
    queryFn: () => api.getTradingPerformance(),
    refetchInterval: 30000,
    retry: false,
  });

  // Fetch models
  const { data: models } = useQuery({
    queryKey: ['trading-models'],
    queryFn: () => api.getTradingModels(),
    refetchInterval: 60000,
    retry: false,
  });

  const queryClient = useQueryClient();
  const [newStockSymbol, setNewStockSymbol] = useState('');
  const [newCryptoSymbol, setNewCryptoSymbol] = useState('');

  const positions = positionsData?.positions ?? [];
  const trades = tradesData?.trades ?? [];
  const signals = signalsData?.signals ?? [];

  const updateWatchlistMutation = useMutation({
    mutationFn: (data: { stocks?: string[], crypto?: string[] }) => 
      api.updateTradingWatchlist(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['trading-status'] });
      setNewStockSymbol('');
      setNewCryptoSymbol('');
    },
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  if (!status?.enabled) {
    return (
      <div className="card text-center">
        <div className="text-slate-400 mb-4">Trading is disabled in configuration</div>
        <div className="text-slate-500 text-sm">Enable trading in config.json to use this feature</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      {/* Portfolio Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Portfolio Value"
          value={formatCurrency(portfolio?.portfolio_value ?? 0)}
          icon={Wallet}
          trend={portfolio?.total_pnl && portfolio.total_pnl > 0 ? 'up' : portfolio?.total_pnl && portfolio.total_pnl < 0 ? 'down' : null}
        />
        <StatCard
          title="Cash Balance"
          value={formatCurrency(portfolio?.cash_balance ?? 0)}
          subtitle={`Available: ${formatCurrency(portfolio?.available_cash ?? 0)}`}
          icon={DollarSign}
        />
        <StatCard
          title="Total P&L"
          value={formatCurrency(portfolio?.total_pnl ?? 0)}
          subtitle={`Unrealized: ${formatCurrency(portfolio?.unrealized_pnl ?? 0)}`}
          icon={portfolio?.total_pnl && portfolio.total_pnl >= 0 ? TrendingUp : TrendingDown}
          trend={portfolio?.total_pnl && portfolio.total_pnl > 0 ? 'up' : portfolio?.total_pnl && portfolio.total_pnl < 0 ? 'down' : null}
        />
        <StatCard
          title="Positions"
          value={portfolio?.positions_count ?? 0}
          icon={Activity}
        />
      </div>

      {/* Performance Metrics */}
      {performance && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="ROI"
            value={formatPercent(performance.roi ?? 0)}
            icon={BarChart3}
            trend={performance.roi > 0 ? 'up' : performance.roi < 0 ? 'down' : null}
          />
          <StatCard
            title="Win Rate"
            value={formatPercent(performance.win_rate ?? 0)}
            subtitle={`${performance.winning_trades ?? 0}W / ${performance.losing_trades ?? 0}L`}
            icon={Target}
          />
          <StatCard
            title="Total Trades"
            value={performance.total_trades ?? 0}
            icon={Activity}
          />
          <StatCard
            title="Sharpe Ratio"
            value={(performance.sharpe_ratio ?? 0).toFixed(2)}
            icon={BarChart3}
          />
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Positions */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-3">
            <Activity size={20} />
            Active Positions ({positions.length})
          </h3>
          {positions.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="No active positions"
              description="Open positions will appear here"
            />
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {positions.map((pos) => (
                <div
                  key={pos.id}
                  className="bg-slate-800/50 rounded-lg p-3 flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{pos.symbol}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        pos.direction === 'long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                      }`}>
                        {pos.direction.toUpperCase()}
                      </span>
                      <span className="text-xs text-slate-500">{pos.strategy}</span>
                    </div>
                    <div className="text-sm text-slate-400 mt-1">
                      {pos.quantity.toFixed(4)} @ {formatCurrency(pos.entry_price)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-medium ${pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(pos.unrealized_pnl)}
                    </div>
                    <div className={`text-sm ${pos.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {pos.pnl_pct >= 0 ? '+' : ''}{pos.pnl_pct.toFixed(2)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Current Signals */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-3">
            <Zap size={20} />
            Current Signals ({signals.length})
          </h3>
          {signals.length === 0 ? (
            <EmptyState
              icon={Zap}
              title="No signals available"
              description="Trading signals will appear here when models are trained"
            />
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {signals.map((signal, idx) => (
                <div
                  key={idx}
                  className="bg-slate-800/50 rounded-lg p-3"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{signal.symbol}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        signal.direction === 'long' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                      }`}>
                        {signal.direction.toUpperCase()}
                      </span>
                      <span className="text-xs text-slate-500">{signal.strategy}</span>
                    </div>
                    <div className="text-sm text-slate-400">
                      Conf: {(signal.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs text-slate-400">
                    <div>Entry: {formatCurrency(signal.entry_price)}</div>
                    <div>SL: {formatCurrency(signal.stop_loss)}</div>
                    <div>TP: {formatCurrency(signal.take_profit)}</div>
                  </div>
                  <div className="flex justify-between mt-2 text-xs">
                    <span className="text-slate-500">R:R {signal.risk_reward.toFixed(1)}</span>
                    <span className={signal.expected_value > 0 ? 'text-emerald-400' : 'text-red-400'}>
                      EV: {(signal.expected_value * 100).toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Trades */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-3">
            <BarChart3 size={20} />
            Recent Trades
          </h3>
          {trades.length === 0 ? (
            <EmptyState
              icon={BarChart3}
              title="No trades yet"
              description="Completed trades will appear here"
            />
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {trades.slice(0, 10).map((trade) => (
                <div
                  key={trade.id}
                  className="bg-slate-800/50 rounded-lg p-3 flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{trade.symbol}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        trade.direction === 'buy' || trade.direction === 'long' 
                          ? 'bg-emerald-500/20 text-emerald-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {trade.direction.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-sm text-slate-400 mt-1">
                      {trade.quantity.toFixed(4)} @ {formatCurrency(trade.price)}
                    </div>
                  </div>
                  <div className="text-right">
                    {trade.pnl !== undefined && trade.pnl !== null && (
                      <div className={`font-medium ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {formatCurrency(trade.pnl)}
                      </div>
                    )}
                    <div className="text-xs text-slate-500">
                      {new Date(trade.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Model Status */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-3">
            <Target size={20} />
            Model Status
          </h3>
          {models && !('error' in models) ? (
            <div className="space-y-3">
              {Object.entries(models)
                .filter(([strategy]) => strategy !== 'error')
                .map(([strategy, model]) => {
                  if (typeof model !== 'object' || model === null) return null;
                  const modelData = model as any;
                  return (
                    <div
                      key={strategy}
                      className="bg-slate-800/50 rounded-lg p-3 flex items-center justify-between"
                    >
                      <div>
                        <div className="font-medium capitalize text-slate-300">{strategy}</div>
                        <div className="text-sm text-slate-400">
                          {modelData.available ? (
                            <>CV Score: {((modelData.cv_score ?? 0) * 100).toFixed(1)}%</>
                          ) : (
                            'Not trained'
                          )}
                        </div>
                      </div>
                      <div className={`px-3 py-1 rounded text-sm ${
                        modelData.available 
                          ? 'bg-emerald-500/20 text-emerald-400' 
                          : 'bg-slate-700/50 text-slate-400'
                      }`}>
                        {modelData.available ? 'Ready' : 'Pending'}
                      </div>
                    </div>
                  );
                })}
            </div>
          ) : (
            <EmptyState
              icon={Target}
              title="Loading models..."
              description="Model status will appear here"
            />
          )}
        </div>
      </div>

      {/* Watchlist Info */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Watchlist</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm text-slate-400">Stocks ({status?.watchlist?.stocks?.length ?? 0})</div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newStockSymbol}
                  onChange={(e) => setNewStockSymbol(e.target.value.toUpperCase())}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newStockSymbol.trim()) {
                      const current = status?.watchlist?.stocks ?? [];
                      if (!current.includes(newStockSymbol.trim())) {
                        updateWatchlistMutation.mutate({
                          stocks: [...current, newStockSymbol.trim()]
                        });
                      }
                    }
                  }}
                  placeholder="Add symbol (e.g., AAPL)"
                  className="bg-slate-800/50 border border-slate-700 rounded px-2 py-1 text-sm w-32 focus:outline-none focus:border-emerald-500"
                />
                <button
                  onClick={() => {
                    if (newStockSymbol.trim()) {
                      const current = status?.watchlist?.stocks ?? [];
                      if (!current.includes(newStockSymbol.trim())) {
                        updateWatchlistMutation.mutate({
                          stocks: [...current, newStockSymbol.trim()]
                        });
                      }
                    }
                  }}
                  disabled={!newStockSymbol.trim() || updateWatchlistMutation.isPending}
                  className="btn-primary flex items-center gap-1 px-2 py-1 text-xs disabled:opacity-50"
                  type="button"
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {status?.watchlist?.stocks?.map((symbol) => (
                <span key={symbol} className="bg-slate-800/50 px-3 py-1 rounded text-sm flex items-center gap-2">
                  {symbol}
                  <button
                    onClick={() => {
                      const current = status?.watchlist?.stocks ?? [];
                      updateWatchlistMutation.mutate({
                        stocks: current.filter(s => s !== symbol)
                      });
                    }}
                    className="hover:text-red-400 transition-colors"
                    type="button"
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm text-slate-400">Crypto ({status?.watchlist?.crypto?.length ?? 0})</div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newCryptoSymbol}
                  onChange={(e) => setNewCryptoSymbol(e.target.value.toUpperCase())}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newCryptoSymbol.trim()) {
                      const current = status?.watchlist?.crypto ?? [];
                      if (!current.includes(newCryptoSymbol.trim())) {
                        updateWatchlistMutation.mutate({
                          crypto: [...current, newCryptoSymbol.trim()]
                        });
                      }
                    }
                  }}
                  placeholder="Add symbol (e.g., BTC-USD)"
                  className="bg-slate-800/50 border border-slate-700 rounded px-2 py-1 text-sm w-32 focus:outline-none focus:border-emerald-500"
                />
                <button
                  onClick={() => {
                    if (newCryptoSymbol.trim()) {
                      const current = status?.watchlist?.crypto ?? [];
                      if (!current.includes(newCryptoSymbol.trim())) {
                        updateWatchlistMutation.mutate({
                          crypto: [...current, newCryptoSymbol.trim()]
                        });
                      }
                    }
                  }}
                  disabled={!newCryptoSymbol.trim() || updateWatchlistMutation.isPending}
                  className="btn-primary flex items-center gap-1 px-2 py-1 text-xs disabled:opacity-50"
                  type="button"
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {status?.watchlist?.crypto?.map((symbol) => (
                <span key={symbol} className="bg-slate-800/50 px-3 py-1 rounded text-sm flex items-center gap-2">
                  {symbol}
                  <button
                    onClick={() => {
                      const current = status?.watchlist?.crypto ?? [];
                      updateWatchlistMutation.mutate({
                        crypto: current.filter(s => s !== symbol)
                      });
                    }}
                    className="hover:text-red-400 transition-colors"
                    type="button"
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
