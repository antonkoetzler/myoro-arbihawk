import { useState, useEffect, useRef, useCallback } from 'react';
import { TASK_START_PATTERNS } from '../utils/constants';
import type { WebSocketLog } from '../types';

interface UseWebSocketLogsReturn {
  logs: WebSocketLog[];
  connected: boolean;
  clearLogs: () => void;
}

/**
 * WebSocket hook for real-time logs
 */
export function useWebSocketLogs(): UseWebSocketLogsReturn {
  const [logs, setLogs] = useState<WebSocketLog[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );

  // Function to clear logs (exposed for external use)
  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  const connect = useCallback(() => {
    // Determine WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(String(event.data)) as WebSocketLog;
          // Ignore ping messages
          if (data.type === 'ping') return;

          // Check if this message indicates a new task starting
          const isTaskStart = TASK_START_PATTERNS.some((pattern) =>
            data.message?.includes(pattern)
          );

          setLogs((prev) => {
            // If a new task is starting, add a separator before the new task log
            // But only if we haven't already added a separator recently (prevent duplicates from replayed logs)
            if (isTaskStart) {
              // Check if the last log was already a separator or if this exact message was already logged
              const lastLog = prev[prev.length - 1];
              const isRecentSeparator = lastLog?.type === 'separator';
              const isDuplicateMessage = prev.some(
                (log) =>
                  log.message === data.message &&
                  log.timestamp === data.timestamp &&
                  log.level === data.level
              );
              
              // Only add separator if:
              // 1. Last log wasn't a separator (avoid duplicate separators)
              // 2. This isn't a duplicate message (avoid duplicate task start logs)
              if (!isRecentSeparator && !isDuplicateMessage) {
                const separator: WebSocketLog = {
                  timestamp: new Date().toISOString(),
                  level: 'info',
                  message: '\n\n=====          NEW TASK STARTED          =====\n',
                  type: 'separator',
                };
                const newLogs = [...prev, separator, data];
                return newLogs.slice(-500);
              }
              // If it's a duplicate, just skip it entirely
              if (isDuplicateMessage) {
                return prev;
              }
            }

            // Prevent duplicates by checking timestamp + message
            // Use a more lenient check - only filter if timestamp AND message match exactly
            // This allows rapid logs with same message but different timestamps
            const isDuplicate = prev.some(
              (log) =>
                log.timestamp === data.timestamp && 
                log.message === data.message &&
                log.level === data.level
            );
            if (isDuplicate) return prev;

            // Keep only last 500 logs
            const newLogs = [...prev, data];
            return newLogs.slice(-500);
          });
        } catch {
          // Silently handle parse errors - invalid messages are ignored
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return { logs, connected, clearLogs };
}
