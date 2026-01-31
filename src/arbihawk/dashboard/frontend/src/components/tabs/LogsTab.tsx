import { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import { Inbox, Copy } from 'lucide-react';
import { EmptyState } from '../EmptyState';
import { getLogLevelColor } from '../../utils/formatters';
import type { WebSocketLog } from '../../types';

interface LogsTabProps {
  wsLogs: WebSocketLog[];
  wsConnected: boolean;
  clearLogs: () => void;
}

interface LogSectionProps {
  title: string;
  logs: WebSocketLog[];
  colorClass: string;
  isSingleView?: boolean;
}

/**
 * Individual log section component with its own scroll management
 */
function LogSection({ title, logs, colorClass, isSingleView }: LogSectionProps) {
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const savedScrollTopRef = useRef<number>(0);
  const previousLogsLengthRef = useRef<number>(0);
  const wasAtBottomBeforeUpdateRef = useRef<boolean>(true);
  const isUserScrollingRef = useRef<boolean>(false);
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isInitialMountRef = useRef(true);

  const checkIfAtBottom = useCallback((container: HTMLDivElement): boolean => {
    const { scrollTop, scrollHeight, clientHeight } = container;
    return Math.abs(scrollHeight - scrollTop - clientHeight) <= 10;
  }, []);

  useLayoutEffect(() => {
    if (logsContainerRef.current && isInitialMountRef.current) {
      const container = logsContainerRef.current;
      container.scrollTop = container.scrollHeight;
      wasAtBottomBeforeUpdateRef.current = true;
      isInitialMountRef.current = false;
    }
  }, []);

  useEffect(() => {
    const container = logsContainerRef.current;
    if (!container || logs.length === 0) return;

    const isNewLogs = logs.length > previousLogsLengthRef.current;

    if (isNewLogs && !isUserScrollingRef.current) {
      wasAtBottomBeforeUpdateRef.current = checkIfAtBottom(container);
      savedScrollTopRef.current = container.scrollTop;
    }
  }, [logs.length, checkIfAtBottom]);

  useLayoutEffect(() => {
    const container = logsContainerRef.current;
    if (!container || logs.length === 0) return;

    const isNewLogs = logs.length > previousLogsLengthRef.current;

    if (!isNewLogs) {
      previousLogsLengthRef.current = logs.length;
      return;
    }

    const shouldAutoScroll = autoScroll && wasAtBottomBeforeUpdateRef.current;

    if (shouldAutoScroll) {
      container.scrollTop = container.scrollHeight;
      wasAtBottomBeforeUpdateRef.current = true;
    } else {
      container.scrollTop = savedScrollTopRef.current;
      wasAtBottomBeforeUpdateRef.current = false;
    }

    previousLogsLengthRef.current = logs.length;
  }, [logs, autoScroll]);

  const handleLogsScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget;

    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }

    isUserScrollingRef.current = true;

    scrollTimeoutRef.current = setTimeout(() => {
      const scrollTop = container.scrollTop;
      const atBottom = checkIfAtBottom(container);

      savedScrollTopRef.current = scrollTop;
      wasAtBottomBeforeUpdateRef.current = atBottom;
      setAutoScroll(atBottom);

      setTimeout(() => {
        isUserScrollingRef.current = false;
      }, 150);
    }, 100);
  }, [checkIfAtBottom]);

  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  const copyAllLogs = useCallback(() => {
    const text = logs
      .map(log => {
        const parts = [log.timestamp, `[${(log.level ?? '').toUpperCase()}]`];
        if (log.domain) parts.push(`[${log.domain}]`);
        if (log.type) parts.push(`[${log.type}]`);
        parts.push(log.message ?? '');
        return parts.join(' ');
      })
      .join('\n');
    void navigator.clipboard.writeText(text);
  }, [logs]);

  return (
    <div className={`${isSingleView ? 'w-full' : 'flex-1'} min-w-0`}>
      <div className='mb-2 flex items-center justify-between'>
        <div className='flex items-center gap-2'>
          <div className={`h-2 w-2 rounded-full ${colorClass}`} />
          <h4 className='text-sm font-semibold text-slate-300'>{title}</h4>
          <span className='text-xs text-slate-500' title={`${logs.length} log entries`}>
            ({logs.length})
          </span>
        </div>
        <div className='flex items-center gap-1'>
          <button
            onClick={copyAllLogs}
            disabled={logs.length === 0}
            className='rounded bg-slate-700/50 p-1.5 text-slate-400 hover:bg-slate-700 hover:text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed'
            type='button'
            title='Copy all logs'
          >
            <Copy className='h-3.5 w-3.5' />
          </button>
          <button
            onClick={() => {
              if (autoScroll) {
                if (logsContainerRef.current) {
                  savedScrollTopRef.current = logsContainerRef.current.scrollTop;
                  wasAtBottomBeforeUpdateRef.current = false;
                }
                setAutoScroll(false);
              } else {
                if (logsContainerRef.current) {
                  const container = logsContainerRef.current;
                  container.scrollTop = container.scrollHeight;
                  wasAtBottomBeforeUpdateRef.current = true;
                  savedScrollTopRef.current = container.scrollTop;
                  setAutoScroll(true);
                }
              }
            }}
            className='rounded bg-slate-700/50 px-2 py-0.5 text-xs text-slate-400 hover:bg-slate-700'
            type='button'
          >
            {autoScroll ? 'Pause' : 'Resume'}
          </button>
        </div>
      </div>
      <div
        ref={logsContainerRef}
        onScroll={handleLogsScroll}
        className='h-[400px] space-y-1 overflow-y-auto rounded-lg bg-slate-950/60 p-3 font-mono text-xs flex flex-col'
      >
        {logs.length > 0 ? (
          logs.map((log, i) => {
            const workerMatch = log.message?.match(/\[WORKER #(\d+)\]/);
            const serviceMatch = log.message?.match(/\[WORKER #\d+\]\s+\[([A-Z]+)\]/);
            const tradingMatch = log.message?.match(/\[TRADING\]/);
            const stocksMatch = log.message?.match(/\[STOCKS\]/);
            const cryptoMatch = log.message?.match(/\[CRYPTO\]/);

            let messageText = log.message || '';

            if (workerMatch) {
              messageText = messageText.replace(workerMatch[0], '').trim();
            }
            if (serviceMatch) {
              messageText = messageText.replace(`[${serviceMatch[1]}]`, '').trim();
            }
            if (tradingMatch) {
              messageText = messageText.replace('[TRADING]', '').trim();
            }
            if (stocksMatch) {
              messageText = messageText.replace('[STOCKS]', '').trim();
            }
            if (cryptoMatch) {
              messageText = messageText.replace('[CRYPTO]', '').trim();
            }

            return (
              <div
                key={`${log.timestamp}-${i}`}
                data-log-index={i}
                className="text-white leading-relaxed"
              >
                <span className='text-slate-500'>{log.timestamp}</span>{' '}
                {workerMatch && (
                  <span className="text-yellow-400 font-semibold">
                    {workerMatch[0]}
                  </span>
                )}
                {workerMatch && ' '}
                {serviceMatch && (
                  <span className="text-orange-400 font-semibold">
                    [{serviceMatch[1]}]
                  </span>
                )}
                {serviceMatch && ' '}
                {stocksMatch && (
                  <span className="text-blue-400 font-semibold">
                    [STOCKS]
                  </span>
                )}
                {stocksMatch && ' '}
                {cryptoMatch && (
                  <span className="text-purple-400 font-semibold">
                    [CRYPTO]
                  </span>
                )}
                {cryptoMatch && ' '}
                <span className={getLogLevelColor(log.level)}>
                  [{log.level?.toUpperCase()}]
                </span>
                {' '}
                <span className="text-white">{messageText}</span>
              </div>
            );
          })
        ) : (
          <EmptyState
            icon={Inbox}
            title='No Logs'
            description='Logs will appear here when automation runs'
          />
        )}
      </div>
    </div>
  );
}

/**
 * Logs tab component - displays real-time logs from WebSocket
 * Separates logs by domain (betting vs trading)
 * Supports single and dual view modes
 */
const LOGS_VIEW_MODE_KEY = 'arbihawk_logs_view_mode';

export function LogsTab({ wsLogs, wsConnected }: LogsTabProps) {
  const [viewMode, setViewMode] = useState<'dual' | 'betting' | 'trading'>(() => {
    const saved = localStorage.getItem(LOGS_VIEW_MODE_KEY);
    return (saved === 'dual' || saved === 'betting' || saved === 'trading') ? saved : 'dual';
  });

  useEffect(() => {
    localStorage.setItem(LOGS_VIEW_MODE_KEY, viewMode);
  }, [viewMode]);

  // Separate logs by domain - use domain field primarily, fallback to message content
  const bettingLogs = wsLogs.filter(log => {
    const domain = log.domain || 'betting';
    // If domain is explicitly set, use it
    if (domain === 'betting') return true;
    if (domain === 'trading') return false;
    // Fallback: check message content for trading indicators
    const isTradingMessage = log.message?.includes('[TRADING]') ||
      log.message?.includes('[STOCKS]') ||
      log.message?.includes('[CRYPTO]') ||
      log.message?.includes('Training MOMENTUM') ||
      log.message?.includes('Training SWING') ||
      log.message?.includes('Training VOLATILITY');
    return !isTradingMessage;
  });

  const tradingLogs = wsLogs.filter(log => {
    const domain = log.domain || 'betting';
    // If domain is explicitly set, use it
    if (domain === 'trading') return true;
    if (domain === 'betting') return false;
    // Fallback: check message content for trading indicators
    const isTradingMessage = log.message?.includes('[TRADING]') ||
      log.message?.includes('[STOCKS]') ||
      log.message?.includes('[CRYPTO]') ||
      log.message?.includes('Training MOMENTUM') ||
      log.message?.includes('Training SWING') ||
      log.message?.includes('Training VOLATILITY');
    return isTradingMessage;
  });

  return (
    <div className='space-y-6'>
      <div className='card'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='text-lg font-semibold'>Execution Logs</h3>
          <div className='flex items-center gap-3'>
            {/* View Mode Toggle */}
            <div className='flex items-center gap-1 rounded-lg bg-slate-800/50 p-1'>
              <button
                onClick={() => setViewMode('dual')}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${viewMode === 'dual'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-slate-400 hover:text-slate-300'
                  }`}
                type='button'
              >
                Dual
              </button>
              <button
                onClick={() => setViewMode('betting')}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${viewMode === 'betting'
                    ? 'bg-sky-500/20 text-sky-400'
                    : 'text-slate-400 hover:text-slate-300'
                  }`}
                type='button'
              >
                Betting
              </button>
              <button
                onClick={() => setViewMode('trading')}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${viewMode === 'trading'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-slate-400 hover:text-slate-300'
                  }`}
                type='button'
              >
                Trading
              </button>
            </div>
            <div
              className={`flex items-center gap-2 rounded px-2 py-1 text-xs ${wsConnected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}
            >
              <div
                className={`h-1.5 w-1.5 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-red-400'}`}
              />
              {wsConnected ? 'Live' : 'Disconnected'}
            </div>
          </div>
        </div>

        {/* Dynamic layout based on view mode */}
        <div className={`flex gap-4 ${viewMode === 'dual' ? '' : ''}`}>
          {(viewMode === 'dual' || viewMode === 'betting') && (
            <LogSection
              title='Betting'
              logs={bettingLogs}
              colorClass='bg-sky-400'
              isSingleView={viewMode !== 'dual'}
            />
          )}
          {(viewMode === 'dual' || viewMode === 'trading') && (
            <LogSection
              title='Trading'
              logs={tradingLogs}
              colorClass='bg-emerald-400'
              isSingleView={viewMode !== 'dual'}
            />
          )}
        </div>
      </div>
    </div>
  );
}
