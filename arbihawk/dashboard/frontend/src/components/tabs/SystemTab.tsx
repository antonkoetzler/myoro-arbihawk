import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Database, HelpCircle, X } from 'lucide-react';
import { EmptyState } from '../EmptyState';
import { Tooltip } from '../Tooltip';
import { dbStatTooltips } from '../../utils/constants';
import type { ErrorsResponse, DbStats } from '../../types';
import type { createApi } from '../../api/api';

interface SystemTabProps {
  api: ReturnType<typeof createApi>;
}

/**
 * System tab component - displays system health, errors, and database stats
 */
export function SystemTab({ api }: SystemTabProps) {
  const queryClient = useQueryClient();

  const { data: errors } = useQuery<ErrorsResponse>({
    queryKey: ['errors'],
    queryFn: api.getErrors,
    refetchInterval: 30000,
    retry: false,
  });

  const { data: dbStats } = useQuery<DbStats>({
    queryKey: ['dbStats'],
    queryFn: api.getDbStats,
    refetchInterval: 30000,
    retry: false,
  });

  const handleDismiss = async (
    errorType: string,
    errorId: number | null,
    errorKey: string | null
  ) => {
    try {
      await api.dismissError(errorType, errorId, errorKey);
      void queryClient.invalidateQueries({ queryKey: ['errors'] });
    } catch {
      // Error handling is done by the API layer
    }
  };

  return (
    <div className='space-y-6'>
      {/* Errors Card - Always visible */}
      <div
        className={`card ${errors?.total_errors && errors.total_errors > 0 ? 'border-red-500/50 bg-red-500/10' : ''}`}
      >
        <div className='flex items-center gap-4'>
          <AlertCircle
            className={
              errors?.total_errors && errors.total_errors > 0
                ? 'text-red-400'
                : 'text-slate-500'
            }
          />
          <div>
            <p
              className={`font-medium ${errors?.total_errors && errors.total_errors > 0 ? 'text-red-400' : 'text-slate-400'}`}
            >
              {errors?.total_errors && errors.total_errors > 0
                ? 'Errors Detected'
                : 'No Errors'}
            </p>
            <p className='text-sm text-slate-400'>
              {errors?.total_errors && errors.total_errors > 0
                ? `${errors.total_errors} error${errors.total_errors !== 1 ? 's' : ''} in the last 24 hours`
                : 'System is running smoothly'}
            </p>
          </div>
        </div>

        {/* Error Details Section */}
        {errors?.total_errors &&
          errors.total_errors > 0 &&
          (() => {
            const visibleLogErrors = errors?.log_errors ?? [];
            const visibleIngestionErrors = errors?.ingestion_errors ?? [];
            const visibleTotal =
              visibleLogErrors.length + visibleIngestionErrors.length;

            if (visibleTotal === 0) {
              return (
                <div className='mt-4 border-t border-slate-700/50 pt-4'>
                  <EmptyState
                    icon={AlertCircle}
                    title='No Errors to Display'
                    description='All errors have been dismissed'
                  />
                </div>
              );
            }

            return (
              <div className='mt-4 space-y-4 border-t border-slate-700/50 pt-4'>
                <p className='text-sm font-medium text-slate-300'>
                  Error Details
                </p>
                <div className='max-h-48 space-y-2 overflow-y-auto'>
                  {visibleLogErrors.map((err) => {
                    const errorKey = `log-${err.timestamp}-${err.message}`;
                    return (
                      <div
                        key={errorKey}
                        className='group relative rounded bg-slate-800/50 p-2 text-sm'
                      >
                        <div className='mb-1 flex items-center gap-2'>
                          <span className='rounded bg-red-500/20 px-2 py-1 text-xs text-red-400'>
                            Log
                          </span>
                          <span className='text-xs text-slate-500'>
                            {err.timestamp}
                          </span>
                        </div>
                        <p className='break-all pr-8 font-mono text-xs text-red-400'>
                          {err.message}
                        </p>
                        <button
                          onClick={() => {
                            void handleDismiss('log', null, errorKey);
                          }}
                          className='absolute right-2 top-2 rounded p-1 opacity-0 transition-opacity hover:bg-slate-700/50 group-hover:opacity-100'
                          title='Dismiss error'
                          type='button'
                        >
                          <X
                            size={14}
                            className='text-slate-400 hover:text-slate-200'
                          />
                        </button>
                      </div>
                    );
                  })}
                  {visibleIngestionErrors.map((err, i) => {
                    return (
                      <div
                        key={`ing-${err.id ?? i}`}
                        className='group relative rounded bg-slate-800/50 p-2 text-sm'
                      >
                        <div className='mb-1 flex items-center gap-2'>
                          <span className='rounded bg-orange-500/20 px-2 py-1 text-xs text-orange-400'>
                            Ingestion
                          </span>
                          <span className='text-xs text-slate-500'>
                            {err.source}
                          </span>
                        </div>
                        <p className='break-all pr-8 font-mono text-xs text-orange-400'>
                          {err.errors ?? 'Validation failed'}
                        </p>
                        <button
                          onClick={() => {
                            void handleDismiss(
                              'ingestion',
                              err.id ?? null,
                              null
                            );
                          }}
                          className='absolute right-2 top-2 rounded p-1 opacity-0 transition-opacity hover:bg-slate-700/50 group-hover:opacity-100'
                          title='Dismiss error'
                          type='button'
                        >
                          <X
                            size={14}
                            className='text-slate-400 hover:text-slate-200'
                          />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}
      </div>

      {/* Database Stats */}
      <div className='card'>
        <h3 className='mb-4 text-lg font-semibold'>Database Stats</h3>
        {dbStats && Object.keys(dbStats).length > 0 ? (
          <div className='grid grid-cols-2 gap-4'>
            {Object.entries(dbStats).map(([key, value]) => (
              <div key={key} className='rounded-lg bg-slate-700/30 p-4'>
                <div className='flex items-center gap-1'>
                  <Tooltip
                    text={
                      dbStatTooltips[key] ??
                      `Number of ${key.replace(/_/g, ' ')}`
                    }
                  >
                    <HelpCircle size={12} className='text-slate-500' />
                  </Tooltip>
                  <p className='text-xs capitalize text-slate-400'>
                    {key.replace(/_/g, ' ')}
                  </p>
                </div>
                <p className='font-mono text-lg'>
                  {typeof value === 'number' ? value.toLocaleString() : value}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={Database}
            title='No Data Yet'
            description='Database statistics will appear here'
          />
        )}
      </div>
    </div>
  );
}
