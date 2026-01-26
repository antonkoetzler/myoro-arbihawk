import { useState, useMemo, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Filter, ArrowUpDown, ArrowUp, ArrowDown, X, Search, Activity, TrendingUp, Database, Target, Clock } from 'lucide-react';
import type { createApi } from '../../api/api';
import type { BetsResponse, TopConfidenceBet } from '../../types';
import { StatCard } from '../StatCard';
import { formatPercent, formatMoney } from '../../utils/formatters';

interface BettingTabProps {
  api: ReturnType<typeof createApi>;
  bankroll?: any;
}

interface Filters {
  result?: string;
  market_name?: string;
  outcome_name?: string;
  tournament_name?: string;
  date_from?: string;
  date_to?: string;
}

type SortColumn = 'odds' | 'stake' | 'payout' | 'placed_at';
type SortDirection = 'asc' | 'desc' | null;
type FilterType = 'date' | 'tournament' | 'market' | 'outcome' | 'result' | null;

/**
 * Betting tab component - displays detailed bet history table with filtering and pagination
 */
export function BettingTab({ api, bankroll }: BettingTabProps) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [filters, setFilters] = useState<Filters>({});
  const [sortColumn, setSortColumn] = useState<SortColumn | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [activeFilter, setActiveFilter] = useState<FilterType>(null);
  const [tempFilterValue, setTempFilterValue] = useState<string>('');
  const [tempDateFrom, setTempDateFrom] = useState<string>('');
  const [tempDateTo, setTempDateTo] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [topBetSortBy, setTopBetSortBy] = useState<'confidence' | 'ev'>('confidence');
  const modalRef = useRef<HTMLDivElement>(null);

  const queryParams = useMemo(() => ({
    ...filters,
    search: searchQuery.trim() || undefined,
    page: searchQuery.trim() ? 1 : page, // Reset to page 1 when searching
    per_page: perPage,
  }), [filters, searchQuery, page, perPage]);

  const { data: betsResponse, isLoading } = useQuery<BetsResponse>({
    queryKey: ['bets', queryParams],
    queryFn: () => api.getBets(queryParams),
    refetchInterval: 30000,
    retry: false,
  });

  const bets = betsResponse?.bets ?? [];
  const totalPages = betsResponse?.total_pages ?? 0;
  const total = betsResponse?.total ?? 0;

  // Get unique values for filter dropdowns
  const { data: filterValues } = useQuery<{ markets: string[]; tournaments: string[] }>({
    queryKey: ['bets-filter-values'],
    queryFn: () => api.getBetFilterValues(),
    retry: false,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const uniqueMarkets = filterValues?.markets ?? [];
  const uniqueTournaments = filterValues?.tournaments ?? [];

  // Fetch top confidence bet
  const { data: topBetData, isLoading: isLoadingTopBet } = useQuery({
    queryKey: ['top-confidence-bet', topBetSortBy],
    queryFn: () => api.getTopConfidenceBet(topBetSortBy, 1),
    refetchInterval: 45000, // Refresh every 45 seconds
    retry: false,
  });

  const topBet: TopConfidenceBet | undefined = topBetData?.bets?.[0];

  // Apply client-side sorting (search is handled server-side)
  const sortedBets = useMemo(() => {
    if (!sortColumn || !sortDirection) return bets;
    
    const sorted = [...bets];
    sorted.sort((a, b) => {
      let aVal: number | string | undefined;
      let bVal: number | string | undefined;

      switch (sortColumn) {
        case 'odds':
          aVal = a.odds;
          bVal = b.odds;
          break;
        case 'stake':
          aVal = a.stake;
          bVal = b.stake;
          break;
        case 'payout':
          aVal = a.payout ?? 0;
          bVal = b.payout ?? 0;
          break;
        case 'placed_at':
          aVal = a.placed_at ? new Date(a.placed_at).getTime() : 0;
          bVal = b.placed_at ? new Date(b.placed_at).getTime() : 0;
          break;
      }

      if (aVal === undefined) return 1;
      if (bVal === undefined) return -1;
      
      const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return sorted;
  }, [bets, sortColumn, sortDirection]);

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      // Cycle: desc -> asc -> null
      if (sortDirection === 'desc') {
        setSortDirection('asc');
      } else if (sortDirection === 'asc') {
        setSortDirection(null);
        setSortColumn(null);
      }
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const openFilter = (filterType: FilterType) => {
    setActiveFilter(filterType);
    // Initialize temp value based on current filter
    switch (filterType) {
      case 'date':
        setTempDateFrom(filters.date_from ?? '');
        setTempDateTo(filters.date_to ?? '');
        break;
      case 'tournament':
        setTempFilterValue(filters.tournament_name ?? '');
        break;
      case 'market':
        setTempFilterValue(filters.market_name ?? '');
        break;
      case 'outcome':
        setTempFilterValue(filters.outcome_name ?? '');
        break;
      case 'result':
        setTempFilterValue(filters.result ?? '');
        break;
    }
  };

  const applyFilter = () => {
    if (!activeFilter) return;

    const newFilters = { ...filters };
    
    switch (activeFilter) {
      case 'date':
        if (tempDateFrom) newFilters.date_from = tempDateFrom;
        else delete newFilters.date_from;
        if (tempDateTo) newFilters.date_to = tempDateTo;
        else delete newFilters.date_to;
        break;
      case 'tournament':
        if (tempFilterValue) newFilters.tournament_name = tempFilterValue;
        else delete newFilters.tournament_name;
        break;
      case 'market':
        if (tempFilterValue) newFilters.market_name = tempFilterValue;
        else delete newFilters.market_name;
        break;
      case 'outcome':
        if (tempFilterValue) newFilters.outcome_name = tempFilterValue;
        else delete newFilters.outcome_name;
        break;
      case 'result':
        if (tempFilterValue) newFilters.result = tempFilterValue;
        else delete newFilters.result;
        break;
    }

    setFilters(newFilters);
    setPage(1);
    setActiveFilter(null);
  };

  const clearFilter = () => {
    if (!activeFilter) return;

    const newFilters = { ...filters };
    switch (activeFilter) {
      case 'date':
        delete newFilters.date_from;
        delete newFilters.date_to;
        break;
      case 'tournament':
        delete newFilters.tournament_name;
        break;
      case 'market':
        delete newFilters.market_name;
        break;
      case 'outcome':
        delete newFilters.outcome_name;
        break;
      case 'result':
        delete newFilters.result;
        break;
    }
    setFilters(newFilters);
    setPage(1);
    setActiveFilter(null);
  };

  const closeModal = () => {
    setActiveFilter(null);
  };

  // Handle click outside modal
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        closeModal();
      }
    };

    if (activeFilter) {
      document.addEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = 'unset';
    };
  }, [activeFilter]);

  const formatDate = (dateString?: string) => {
    if (!dateString) return { date: '-', time: '' };
    try {
      // Parse date - if no timezone info, assume UTC (SQLite stores UTC)
      let date: Date;
      // Check if date string has timezone indicator (Z, +HH:MM, or -HH:MM)
      const hasTimezone = /[Z+-]\d{2}:?\d{2}$/.test(dateString) || dateString.endsWith('Z');
      if (hasTimezone) {
        // Has timezone info, parse normally (will convert to local timezone)
        date = new Date(dateString);
      } else {
        // No timezone info, assume UTC and append 'Z' to force UTC parsing
        date = new Date(dateString + 'Z');
      }
      
      // Use local timezone methods (getDate, getHours, etc. automatically use local timezone)
      const day = String(date.getDate()).padStart(2, '0');
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const year = date.getFullYear();
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      
      return {
        date: `${day}/${month}/${year}`,
        time: `${hours}:${minutes}:${seconds}`
      };
    } catch {
      return { date: dateString, time: '' };
    }
  };

  const getSortIcon = (column: SortColumn) => {
    if (sortColumn !== column) {
      return <ArrowUpDown size={14} className='inline ml-1 text-slate-500' />;
    }
    if (sortDirection === 'asc') {
      return <ArrowUp size={14} className='inline ml-1 text-slate-300' />;
    }
    if (sortDirection === 'desc') {
      return <ArrowDown size={14} className='inline ml-1 text-slate-300' />;
    }
    return <ArrowUpDown size={14} className='inline ml-1 text-slate-500' />;
  };

  const renderFilterModal = () => {
    if (!activeFilter) return null;

    const modalContent = (
      <div 
        className='fixed inset-0 z-[9999] flex items-center justify-center bg-black/50'
        style={{ 
          position: 'fixed', 
          top: 0, 
          left: 0, 
          right: 0, 
          bottom: 0,
          width: '100vw',
          height: '100vh',
          margin: 0,
          padding: 0
        }}
      >
        <div 
          ref={modalRef}
          className='w-full max-w-md rounded-lg bg-slate-800 p-6 shadow-xl'
          onClick={(e) => e.stopPropagation()}
        >
          <div className='mb-4 flex items-center justify-between'>
            <h3 className='text-lg font-semibold'>
              Filter by {activeFilter === 'date' ? 'Date' : activeFilter === 'tournament' ? 'League/Tournament' : activeFilter === 'market' ? 'Market' : activeFilter === 'outcome' ? 'Outcome' : 'Result'}
            </h3>
            <button
              onClick={closeModal}
              className='text-slate-400 hover:text-slate-200'
            >
              <X size={20} />
            </button>
          </div>

          <div className='space-y-4'>
            {activeFilter === 'date' && (
              <div className='space-y-3'>
                <div className='flex flex-col gap-1'>
                  <label className='text-sm text-slate-400'>Date From</label>
                  <input
                    type='date'
                    value={tempDateFrom}
                    onChange={(e) => setTempDateFrom(e.target.value)}
                    className='w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-slate-600 focus:outline-none'
                  />
                </div>
                <div className='flex flex-col gap-1'>
                  <label className='text-sm text-slate-400'>Date To</label>
                  <input
                    type='date'
                    value={tempDateTo}
                    onChange={(e) => setTempDateTo(e.target.value)}
                    className='w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-slate-600 focus:outline-none'
                  />
                </div>
              </div>
            )}

            {activeFilter === 'tournament' && (
              <div className='flex flex-col gap-1'>
                <label className='text-sm text-slate-400'>League/Tournament</label>
                <select
                  value={tempFilterValue}
                  onChange={(e) => setTempFilterValue(e.target.value)}
                  className='w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-slate-600 focus:outline-none'
                >
                  <option value=''>All Leagues</option>
                  {uniqueTournaments.map(tournament => (
                    <option key={tournament} value={tournament}>{tournament}</option>
                  ))}
                </select>
              </div>
            )}

            {activeFilter === 'market' && (
              <div className='flex flex-col gap-1'>
                <label className='text-sm text-slate-400'>Market</label>
                <select
                  value={tempFilterValue}
                  onChange={(e) => setTempFilterValue(e.target.value)}
                  className='w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-slate-600 focus:outline-none'
                >
                  <option value=''>All Markets</option>
                  {uniqueMarkets.map(market => (
                    <option key={market} value={market}>{market}</option>
                  ))}
                </select>
              </div>
            )}

            {activeFilter === 'outcome' && (
              <div className='flex flex-col gap-1'>
                <label className='text-sm text-slate-400'>Outcome</label>
                <input
                  type='text'
                  value={tempFilterValue}
                  onChange={(e) => setTempFilterValue(e.target.value)}
                  placeholder='Filter by outcome...'
                  className='w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-slate-600 focus:outline-none'
                />
              </div>
            )}

            {activeFilter === 'result' && (
              <div className='flex flex-col gap-1'>
                <label className='text-sm text-slate-400'>Result</label>
                <select
                  value={tempFilterValue}
                  onChange={(e) => setTempFilterValue(e.target.value)}
                  className='w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-slate-600 focus:outline-none'
                >
                  <option value=''>All</option>
                  <option value='win'>Win</option>
                  <option value='loss'>Loss</option>
                  <option value='pending'>Pending</option>
                </select>
              </div>
            )}
          </div>

          <div className='mt-6 flex justify-end gap-3'>
            <button
              onClick={clearFilter}
              className='rounded border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700'
            >
              Clear
            </button>
            <button
              onClick={applyFilter}
              className='rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700'
            >
              Apply
            </button>
          </div>
        </div>
      </div>
    );

    return createPortal(modalContent, document.body);
  };

  // Determine win rate trend
  const getWinRateTrend = (): 'up' | 'down' | null => {
    const wins = bankroll?.wins ?? 0;
    const losses = bankroll?.losses ?? 0;
    if (wins === 0 && losses === 0) return null;
    return (bankroll?.win_rate ?? 0) > 0.5 ? 'up' : 'down';
  };

  // Format start time
  const formatStartTime = (startTime?: string) => {
    if (!startTime) return '';
    try {
      const date = new Date(startTime);
      const now = new Date();
      const diffMs = date.getTime() - now.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      
      if (diffMs < 0) {
        return 'Started';
      } else if (diffHours > 0) {
        return `in ${diffHours}h ${diffMins}m`;
      } else {
        return `in ${diffMins}m`;
      }
    } catch {
      return startTime;
    }
  };

  // Get confidence color
  const getConfidenceColor = (probability: number) => {
    if (probability >= 0.7) return 'text-emerald-400';
    if (probability >= 0.5) return 'text-yellow-400';
    return 'text-orange-400';
  };

  // Get EV color
  const getEVColor = (ev: number) => {
    if (ev >= 0.1) return 'text-emerald-400';
    if (ev >= 0.05) return 'text-yellow-400';
    return 'text-orange-400';
  };

  return (
    <div className='space-y-6'>
      {/* Top Confidence Bet Hero Card */}
      <div className='card border-2 border-emerald-500/30 bg-gradient-to-br from-slate-800 to-slate-900'>
        <div className='mb-4 flex items-center justify-between'>
          <div className='flex items-center gap-3'>
            <div className='rounded-lg bg-emerald-500/20 p-2'>
              <Target className='text-emerald-400' size={24} />
            </div>
            <div>
              <h2 className='text-xl font-bold text-slate-100'>Today's Top Bet</h2>
              <p className='text-sm text-slate-400'>Most confident recommendation for today</p>
            </div>
          </div>
          <div className='flex gap-2'>
            <button
              onClick={() => setTopBetSortBy('confidence')}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                topBetSortBy === 'confidence'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              Highest Confidence
            </button>
            <button
              onClick={() => setTopBetSortBy('ev')}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                topBetSortBy === 'ev'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              Best Value (EV)
            </button>
          </div>
        </div>

        {isLoadingTopBet ? (
          <div className='py-8 text-center text-slate-400'>
            <div className='inline-block h-8 w-8 animate-spin rounded-full border-4 border-slate-600 border-t-emerald-500'></div>
            <p className='mt-2'>Loading top bet...</p>
          </div>
        ) : topBet ? (
          <div className='grid grid-cols-1 gap-6 md:grid-cols-3'>
            {/* Match Info */}
            <div className='space-y-3'>
              <div>
                <p className='text-xs text-slate-400'>Match</p>
                <p className='text-lg font-semibold text-slate-100'>
                  {topBet.home_team} vs {topBet.away_team}
                </p>
                {topBet.tournament_name && (
                  <p className='text-sm text-slate-400'>{topBet.tournament_name}</p>
                )}
              </div>
              <div className='flex items-center gap-2 text-sm text-slate-400'>
                <Clock size={14} />
                <span>{formatStartTime(topBet.start_time)}</span>
              </div>
            </div>

            {/* Bet Recommendation */}
            <div className='space-y-3'>
              <div>
                <p className='text-xs text-slate-400'>Recommendation</p>
                <p className='text-lg font-semibold text-slate-100'>{topBet.outcome}</p>
                <p className='text-sm text-slate-400'>{topBet.market}</p>
              </div>
              <div className='flex items-center gap-2'>
                <span className='text-sm text-slate-400'>Odds:</span>
                <span className='text-lg font-mono font-semibold text-slate-100'>{topBet.odds.toFixed(2)}</span>
              </div>
              {topBet.bookmaker && (
                <p className='text-xs text-slate-500'>via {topBet.bookmaker}</p>
              )}
            </div>

            {/* Metrics */}
            <div className='space-y-3'>
              <div>
                <p className='text-xs text-slate-400'>Confidence</p>
                <p className={`text-2xl font-bold ${getConfidenceColor(topBet.probability)}`}>
                  {(topBet.probability * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className='text-xs text-slate-400'>Expected Value</p>
                <p className={`text-xl font-semibold ${getEVColor(topBet.expected_value)}`}>
                  {(topBet.expected_value * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className='py-8 text-center text-slate-400'>
            <Target className='mx-auto mb-2 opacity-50' size={32} />
            <p className='text-sm'>
              {topBetData?.message || 'No confident bets found for today'}
            </p>
            <p className='mt-1 text-xs text-slate-500'>
              Check back later or run data collection and training
            </p>
          </div>
        )}
      </div>

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

      {/* Per-Model Performance */}
      {bankroll?.by_model && Object.keys(bankroll.by_model).length > 0 && (
        <div className='card'>
          <h3 className='mb-4 text-lg font-semibold'>Performance by Model</h3>
          <div className='grid grid-cols-1 gap-4 md:grid-cols-3'>
            {Object.entries(bankroll.by_model).map(([market, stats]: [string, any]) => (
              <div key={market} className='rounded-lg bg-slate-800/50 p-4'>
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

      <div className='card'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='text-lg font-semibold'>Bet History</h3>
          <div className='flex items-center gap-2'>
            <div className='relative'>
              <Search size={16} className='absolute left-3 top-1/2 -translate-y-1/2 text-slate-400' />
              <input
                type='text'
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1); // Reset to page 1 when searching
                }}
                placeholder='Search bets...'
                className='w-64 rounded-lg border border-slate-700 bg-slate-800/50 pl-9 pr-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-emerald-500 focus:outline-none'
              />
            </div>
          </div>
        </div>

        {/* Pagination at top */}
        {totalPages > 1 && (
          <div className='mb-4 flex items-center justify-between'>
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className='flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700'
            >
              <ChevronLeft size={16} />
              Previous
            </button>
            <div className='text-sm text-slate-400'>
              Page {page} of {totalPages}
            </div>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className='flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700'
            >
              Next
              <ChevronRight size={16} />
            </button>
          </div>
        )}

        {/* Table */}
        <div className='overflow-x-auto'>
          <table className='w-full text-sm'>
            <thead>
              <tr className='border-b border-slate-700 text-slate-400'>
                <th className='pb-3 pr-4 text-center min-w-[120px]'>
                  <button
                    onClick={() => openFilter('date')}
                    className='w-full flex items-center justify-center hover:text-slate-300'
                  >
                    Date
                    <Filter size={14} className='ml-1' />
                  </button>
                </th>
                <th className='pb-3 pr-4 text-center'>
                  <button
                    onClick={() => openFilter('tournament')}
                    className='w-full flex items-center justify-center hover:text-slate-300'
                  >
                    League/Tournament
                    <Filter size={14} className='ml-1' />
                  </button>
                </th>
                <th className='pb-3 pr-4 text-center'>
                  <button
                    onClick={() => openFilter('market')}
                    className='w-full flex items-center justify-center hover:text-slate-300'
                  >
                    Market
                    <Filter size={14} className='ml-1' />
                  </button>
                </th>
                <th className='pb-3 pr-4 text-center'>
                  <button
                    onClick={() => openFilter('outcome')}
                    className='w-full flex items-center justify-center hover:text-slate-300'
                  >
                    Outcome
                    <Filter size={14} className='ml-1' />
                  </button>
                </th>
                <th className='pb-3 pr-4 text-center'>
                  <button
                    onClick={() => handleSort('odds')}
                    className='w-full flex items-center justify-center hover:text-slate-300'
                  >
                    Multiplier
                    {getSortIcon('odds')}
                  </button>
                </th>
                <th className='pb-3 pr-4 text-center'>
                  <button
                    onClick={() => handleSort('stake')}
                    className='w-full flex items-center justify-center hover:text-slate-300'
                  >
                    Stake
                    {getSortIcon('stake')}
                  </button>
                </th>
                <th className='pb-3 text-center'>
                  <button
                    onClick={() => openFilter('result')}
                    className='w-full flex items-center justify-center hover:text-slate-300'
                  >
                    Result
                    <Filter size={14} className='ml-1' />
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className='py-8 text-center text-slate-400'>
                    Loading...
                  </td>
                </tr>
              ) : sortedBets.length === 0 ? (
                <tr>
                  <td colSpan={7} className='py-8 text-center text-slate-400'>
                    {searchQuery ? 'No bets match your search' : 'No bets found'}
                  </td>
                </tr>
              ) : (
                sortedBets.map((bet, i) => {
                  const dateFormatted = formatDate(bet.placed_at);
                  const result = bet.result ?? 'pending';
                  let resultDisplay: string;
                  let resultClassName: string;
                  
                  if (result === 'pending') {
                    resultDisplay = 'Pending';
                    resultClassName = 'text-white';
                  } else if (result === 'win') {
                    const winAmount = bet.payout ?? (bet.stake && bet.odds ? bet.stake * bet.odds : 0);
                    resultDisplay = `+$${winAmount.toFixed(2)}`;
                    resultClassName = 'text-emerald-400';
                  } else {
                    // loss
                    resultDisplay = `-$${bet.stake?.toFixed(2) ?? '0.00'}`;
                    resultClassName = 'text-red-400';
                  }
                  
                  return (
                    <tr
                      key={i}
                      className={
                        i < sortedBets.length - 1
                          ? 'border-b border-slate-700/50'
                          : ''
                      }
                    >
                      <td className='py-3 pr-4 text-center min-w-[120px]'>
                        <div className='flex flex-col items-center'>
                          <span className='text-slate-300'>{dateFormatted.date}</span>
                          {dateFormatted.time && (
                            <span className='text-xs text-slate-400'>{dateFormatted.time}</span>
                          )}
                        </div>
                      </td>
                      <td className='py-3 pr-4 text-center'>{bet.tournament_name ?? '-'}</td>
                      <td className='py-3 pr-4 text-center'>{bet.market_name ?? '-'}</td>
                      <td className='py-3 pr-4 text-center'>{bet.outcome_name ?? '-'}</td>
                      <td className='py-3 pr-4 text-center font-mono'>
                        {bet.odds}
                      </td>
                      <td className='py-3 pr-4 text-center font-mono'>
                        ${bet.stake?.toFixed(2)}
                      </td>
                      <td className={`py-3 text-center font-mono ${resultClassName}`}>
                        {resultDisplay}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Per Page Selector and Count at bottom */}
        <div className='mt-4 flex items-center justify-between'>
          <div className='text-xs text-slate-400'>
            {searchQuery ? (
              <>Showing {sortedBets.length} of {total} bets (search: "{searchQuery}")</>
            ) : (
              <>Showing {bets.length > 0 ? (page - 1) * perPage + 1 : 0} - {Math.min(page * perPage, total)} of {total} bets</>
            )}
          </div>
          <div className='flex items-center gap-2'>
            <label className='text-xs text-slate-400'>Show:</label>
            <select
              value={perPage}
              onChange={(e) => {
                setPerPage(Number(e.target.value));
                setPage(1);
              }}
              className='rounded border border-slate-700 bg-slate-800 px-2 py-1 text-sm text-slate-200 focus:border-slate-600 focus:outline-none'
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
            <span className='text-xs text-slate-400'>per page</span>
          </div>
        </div>
      </div>

      {/* Filter Modals */}
      {renderFilterModal()}
    </div>
  );
}
