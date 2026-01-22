import { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import { Inbox } from 'lucide-react';
import { EmptyState } from '../EmptyState';
import { getLogLevelColor } from '../../utils/formatters';
import type { WebSocketLog } from '../../types';

interface LogsTabProps {
  wsLogs: WebSocketLog[];
  wsConnected: boolean;
  clearLogs: () => void;
}

/**
 * Logs tab component - displays real-time logs from WebSocket
 */
export function LogsTab({ wsLogs, wsConnected }: LogsTabProps) {
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const savedScrollTopRef = useRef<number>(0);
  const previousLogsLengthRef = useRef<number>(0);
  const wasAtBottomBeforeUpdateRef = useRef<boolean>(true);
  const isUserScrollingRef = useRef<boolean>(false);
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isInitialMountRef = useRef(true);

  // Helper to check if at bottom
  const checkIfAtBottom = useCallback((container: HTMLDivElement): boolean => {
    const { scrollTop, scrollHeight, clientHeight } = container;
    return Math.abs(scrollHeight - scrollTop - clientHeight) <= 10;
  }, []);

  // Initialize: scroll to bottom and enable auto-scroll when tab is first shown
  useLayoutEffect(() => {
    if (logsContainerRef.current && isInitialMountRef.current) {
      const container = logsContainerRef.current;
      container.scrollTop = container.scrollHeight;
      wasAtBottomBeforeUpdateRef.current = true;
      isInitialMountRef.current = false;
    }
  }, []);

  // Check position BEFORE logs update - this runs before the scroll effect
  useEffect(() => {
    const container = logsContainerRef.current;
    if (!container || wsLogs.length === 0) return;

    const isNewLogs = wsLogs.length > previousLogsLengthRef.current;

    if (isNewLogs && !isUserScrollingRef.current) {
      // Capture if we were at bottom BEFORE new content arrives
      wasAtBottomBeforeUpdateRef.current = checkIfAtBottom(container);
      // Save current scroll position for maintaining it if not auto-scrolling
      savedScrollTopRef.current = container.scrollTop;
    }
  }, [wsLogs.length, checkIfAtBottom]);

  // Handle new logs: auto-scroll to bottom or maintain exact scroll position
  useLayoutEffect(() => {
    const container = logsContainerRef.current;
    if (!container || wsLogs.length === 0) return;

    const isNewLogs = wsLogs.length > previousLogsLengthRef.current;

    if (!isNewLogs) {
      previousLogsLengthRef.current = wsLogs.length;
      return;
    }

    // Use the ref value captured BEFORE the update
    const shouldAutoScroll = autoScroll && wasAtBottomBeforeUpdateRef.current;

    if (shouldAutoScroll) {
      // Auto-scroll: keep at bottom
      container.scrollTop = container.scrollHeight;
      wasAtBottomBeforeUpdateRef.current = true;
    } else {
      // No auto-scroll: maintain exact scroll position (pixel value)
      container.scrollTop = savedScrollTopRef.current;
      wasAtBottomBeforeUpdateRef.current = false;
    }

    previousLogsLengthRef.current = wsLogs.length;
  }, [wsLogs, autoScroll]);

  // Throttled scroll handler to prevent excessive state updates
  const handleLogsScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget;

    // Clear existing timeout
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }

    // Mark that user is scrolling
    isUserScrollingRef.current = true;

    // Throttle: only update state after user stops scrolling for 100ms
    scrollTimeoutRef.current = setTimeout(() => {
      const scrollTop = container.scrollTop;
      const atBottom = checkIfAtBottom(container);

      // Save current scroll position
      savedScrollTopRef.current = scrollTop;
      wasAtBottomBeforeUpdateRef.current = atBottom;

      // Update auto-scroll state based on position
      // If user manually scrolls to bottom, re-enable auto-scroll
      setAutoScroll(atBottom);

      // Reset user scrolling flag after a brief delay
      setTimeout(() => {
        isUserScrollingRef.current = false;
      }, 150);
    }, 100);
  }, [checkIfAtBottom]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className='space-y-6'>
      <div className='card'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='text-lg font-semibold'>Execution Logs</h3>
          <div className='flex items-center gap-2'>
            <div
              className={`flex items-center gap-2 rounded px-2 py-1 text-xs ${wsConnected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}
            >
              <div
                className={`h-1.5 w-1.5 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-red-400'}`}
              />
              {wsConnected ? 'Live' : 'Disconnected'}
            </div>
            <button
              onClick={() => {
                if (autoScroll) {
                  // Pausing: save current position
                  if (logsContainerRef.current) {
                    savedScrollTopRef.current = logsContainerRef.current.scrollTop;
                    wasAtBottomBeforeUpdateRef.current = false;
                  }
                  setAutoScroll(false);
                } else {
                  // Resuming: scroll to bottom and enable
                  if (logsContainerRef.current) {
                    const container = logsContainerRef.current;
                    container.scrollTop = container.scrollHeight;
                    wasAtBottomBeforeUpdateRef.current = true;
                    savedScrollTopRef.current = container.scrollTop;
                    setAutoScroll(true);
                  }
                }
              }}
              className='rounded bg-sky-500/20 px-2 py-1 text-xs text-sky-400 hover:bg-sky-500/30'
              type='button'
            >
              {autoScroll ? 'Pause Auto-scroll' : 'Resume Auto-scroll'}
            </button>
          </div>
        </div>
        <div
          ref={logsContainerRef}
          onScroll={handleLogsScroll}
          className='max-h-[500px] space-y-1 overflow-y-auto rounded-lg bg-slate-900/50 p-4 font-mono text-sm'
        >
          {wsLogs.length > 0 ? (
            wsLogs.map((log, i) => {
              // Parse message for worker/service prefixes
              // Format: [WORKER #X] [SERVICE] message
              const workerMatch = log.message?.match(/\[WORKER #(\d+)\]/);
              const serviceMatch = log.message?.match(/\[WORKER #\d+\]\s+\[([A-Z]+)\]/);

              let formattedMessage = log.message || '';
              let messageText = formattedMessage;

              // Extract worker and service, remove them from message
              if (workerMatch) {
                messageText = messageText.replace(workerMatch[0], '').trim();
              }
              if (serviceMatch) {
                messageText = messageText.replace(`[${serviceMatch[1]}]`, '').trim();
              }

              return (
                <div
                  key={`${log.timestamp}-${i}`}
                  data-log-index={i}
                  className="text-white"
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
              title='No Logs Yet'
              description='Logs will appear here when automation runs'
            />
          )}
        </div>
      </div>
    </div>
  );
}
