import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Database, HelpCircle, X, RotateCcw, AlertTriangle, Copy } from 'lucide-react';
import { EmptyState } from '../EmptyState';
import { Tooltip } from '../Tooltip';
import { dbStatTooltips } from '../../utils/constants';
import type { ErrorsResponse, DbStats, EnvironmentConfig } from '../../types';
import type { createApi } from '../../api/api';

interface SystemTabProps {
  api: ReturnType<typeof createApi>;
  showToast: (message: string, type?: 'success' | 'error' | 'info', duration?: number) => void;
}

/**
 * System tab component - displays system health, errors, and database stats
 */
export function SystemTab({ api, showToast }: SystemTabProps) {
  const queryClient = useQueryClient();
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [preserveModels, setPreserveModels] = useState(true);
  const [isResetting, setIsResetting] = useState(false);
  const [showSyncConfirm, setShowSyncConfirm] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const { data: environment } = useQuery<EnvironmentConfig>({
    queryKey: ['environment'],
    queryFn: api.getEnvironment,
    refetchInterval: false,
    retry: false,
  });

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

  const handleReset = async () => {
    setIsResetting(true);
    try {
      const result = await api.resetDatabase(preserveModels);
      showToast(
        `Database reset complete. ${result.total_deleted.toLocaleString()} records deleted. Backup: ${result.backup_path.split('/').pop()}`,
        'success',
        10000
      );
      setShowResetConfirm(false);
      void queryClient.invalidateQueries({ queryKey: ['dbStats'] });
    } catch (err) {
      // Error already handled by API layer
    } finally {
      setIsResetting(false);
    }
  };

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

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const result = await api.syncProdToDebug();
      showToast(
        `Sync complete. ${result.total_copied.toLocaleString()} records copied from production to debug.`,
        'success',
        10000
      );
      setShowSyncConfirm(false);
      void queryClient.invalidateQueries({ queryKey: ['dbStats'] });
      void queryClient.invalidateQueries({ queryKey: ['models'] });
      void queryClient.invalidateQueries({ queryKey: ['bankroll'] });
    } catch (err) {
      // Error already handled by API layer
    } finally {
      setIsSyncing(false);
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
        <h3 className='mb-4 text-lg font-semibold flex items-center gap-3'>
          <Database size={20} />
          Database Stats
        </h3>
        {dbStats && Object.keys(dbStats).length > 0 ? (
          <div className='grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4'>
            {Object.entries(dbStats).map(([key, value]) => (
              <div key={key} className='rounded-lg bg-slate-800/50 p-4'>
                <div className='flex items-center gap-2 mb-2'>
                  <Tooltip
                    text={
                      dbStatTooltips[key] ??
                      `Number of ${key.replace(/_/g, ' ')}`
                    }
                  >
                    <HelpCircle size={14} className='text-slate-500' />
                  </Tooltip>
                  <p className='text-xs capitalize text-slate-400'>
                    {key.replace(/_/g, ' ')}
                  </p>
                </div>
                <p className='font-mono text-xl font-semibold text-slate-300'>
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

      {/* Database Management */}
      <div className='card'>
        <h3 className='mb-4 text-lg font-semibold flex items-center gap-3'>
          <Database size={20} />
          Database Management
        </h3>

        {/* Database Sync Section (Debug only) */}
        {environment?.environment === 'debug' && (
          <div className='mt-6 border-t border-slate-700/50 pt-6'>
            <div className='flex items-center justify-between'>
              <div>
                <h4 className='mb-1 text-sm font-semibold text-slate-300'>
                  Sync from Production
                </h4>
                <p className='text-xs text-slate-400'>
                  Copy all data from production database to debug. Existing debug data will be replaced.
                </p>
              </div>
              {!showSyncConfirm ? (
                <button
                  onClick={() => setShowSyncConfirm(true)}
                  className='flex items-center gap-2 rounded-lg bg-blue-500/20 px-4 py-2 text-sm font-medium text-blue-400 transition-colors hover:bg-blue-500/30'
                >
                  <Copy size={16} />
                  Sync from Production
                </button>
              ) : (
                <div className='flex items-center gap-2'>
                  <button
                    onClick={handleSync}
                    disabled={isSyncing}
                    className='flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-600 disabled:opacity-50'
                  >
                    {isSyncing ? 'Syncing...' : 'Confirm Sync'}
                  </button>
                  <button
                    onClick={() => setShowSyncConfirm(false)}
                    disabled={isSyncing}
                    className='rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-600 disabled:opacity-50'
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
            {showSyncConfirm && (
              <div className='mt-4 flex items-start gap-3 rounded-lg border border-blue-500/30 bg-blue-500/10 p-3'>
                <AlertTriangle size={20} className='mt-0.5 text-blue-500' />
                <div className='flex-1 text-xs text-blue-200'>
                  <p className='font-medium'>This will replace all debug data with production data.</p>
                  <p className='mt-1 text-blue-300/80'>
                    All fixtures, odds, scores, bets, models, and metadata will be copied from production.
                    Existing debug data will be cleared first.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Database Reset Section */}
        <div>
          <div className='flex items-center justify-between'>
            <div>
              <h4 className='mb-1 text-sm font-semibold text-slate-300'>
                Database Reset ({environment?.environment === 'debug' ? 'Debug' : 'Production'})
              </h4>
              <p className='text-xs text-slate-400'>
                Clear all data tables and start fresh. A backup will be created automatically.
              </p>
            </div>
            {!showResetConfirm ? (
              <button
                onClick={() => setShowResetConfirm(true)}
                className='flex items-center gap-2 rounded-lg bg-red-500/20 px-4 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/30'
              >
                <RotateCcw size={16} />
                Reset Database
              </button>
            ) : (
              <div className='flex items-center gap-2'>
                <label className='flex items-center gap-2 text-sm text-slate-300'>
                  <input
                    type='checkbox'
                    checked={preserveModels}
                    onChange={(e) => setPreserveModels(e.target.checked)}
                    className='rounded border-slate-600 bg-slate-700'
                  />
                  Preserve Models
                </label>
                <button
                  onClick={handleReset}
                  disabled={isResetting}
                  className='flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-600 disabled:opacity-50'
                >
                  {isResetting ? 'Resetting...' : 'Confirm Reset'}
                </button>
                <button
                  onClick={() => setShowResetConfirm(false)}
                  disabled={isResetting}
                  className='rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-600 disabled:opacity-50'
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
          {showResetConfirm && (
            <div className='mt-4 flex items-start gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3'>
              <AlertTriangle size={20} className='mt-0.5 text-yellow-500' />
              <div className='flex-1 text-xs text-yellow-200'>
                <p className='font-medium'>Warning: This action cannot be undone!</p>
                <p className='mt-1 text-yellow-300/80'>
                  All fixtures, odds, scores, bets, and ingestion metadata will be deleted.
                  {preserveModels ? ' Model versions will be preserved.' : ' Model versions will also be deleted.'}
                  A backup will be created before resetting.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
