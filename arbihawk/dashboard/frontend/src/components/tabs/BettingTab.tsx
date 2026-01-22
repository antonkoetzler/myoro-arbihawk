import { useState, useMemo, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useQuery } from '@tanstack/react-query';
import { Download, ChevronLeft, ChevronRight, Filter, ArrowUpDown, ArrowUp, ArrowDown, X } from 'lucide-react';
import type { createApi } from '../../api/api';
import type { BetsResponse, Bet } from '../../types';

interface BettingTabProps {
  api: ReturnType<typeof createApi>;
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
export function BettingTab({ api }: BettingTabProps) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [filters, setFilters] = useState<Filters>({});
  const [sortColumn, setSortColumn] = useState<SortColumn | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [activeFilter, setActiveFilter] = useState<FilterType>(null);
  const [tempFilterValue, setTempFilterValue] = useState<string>('');
  const [tempDateFrom, setTempDateFrom] = useState<string>('');
  const [tempDateTo, setTempDateTo] = useState<string>('');
  const modalRef = useRef<HTMLDivElement>(null);

  const queryParams = useMemo(() => ({
    ...filters,
    page,
    per_page: perPage,
  }), [filters, page, perPage]);

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

  // Apply client-side sorting for numeric columns
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
      const date = new Date(dateString);
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

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <h2 className='text-xl font-semibold'>Betting Performance</h2>
        <a
          href='/api/bets/export?format=csv'
          className='btn-secondary flex items-center gap-2'
        >
          <Download size={16} /> Export CSV
        </a>
      </div>

      <div className='card'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='text-lg font-semibold'>Bet History</h3>
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
                    No bets found
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
            Showing {bets.length > 0 ? (page - 1) * perPage + 1 : 0} - {Math.min(page * perPage, total)} of {total} bets
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
