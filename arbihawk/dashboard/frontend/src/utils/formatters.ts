import type { WebSocketLog } from '../types';

/**
 * Format a decimal value as a percentage string
 * @param val - Decimal value (0-1)
 * @returns Formatted percentage string
 */
export const formatPercent = (val: number | undefined | null): string => {
  return val ? `${(val * 100).toFixed(1)}%` : '0%';
};

/**
 * Format a number as a currency string
 * @param val - Numeric value
 * @returns Formatted currency string
 */
export const formatMoney = (val: number | undefined | null): string => {
  return val
    ? `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '$0.00';
};

/**
 * Get log level color class
 * @param level - Log level (error, warning, info, success, ok)
 * @returns Tailwind color class
 */
export const getLogLevelColor = (level: WebSocketLog['level']): string => {
  switch (level?.toLowerCase()) {
    case 'error':
      return 'text-red-400';
    case 'warning':
      return 'text-yellow-400';
    case 'info':
      return 'text-sky-400';
    case 'success':
    case 'ok':
      return 'text-emerald-400';
    default:
      return 'text-slate-300';
  }
};
