import { env } from './env';

/**
 * Simple logger utility.
 *
 * Filters console.log in production while keeping errors and warnings.
 * All logs are prefixed with context for easier debugging.
 */
const isDev = env.NODE_ENV === 'development';

export const logger = {
  /**
   * Logs information (only in development).
   *
   * @param args - Arguments to log
   */
  log: (...args: unknown[]) => {
    if (isDev) {
      console.log(...args);
    }
  },

  /**
   * Logs errors (always logged).
   *
   * @param args - Arguments to log
   */
  error: (...args: unknown[]) => {
    console.error(...args);
  },

  /**
   * Logs warnings (always logged).
   *
   * @param args - Arguments to log
   */
  warn: (...args: unknown[]) => {
    console.warn(...args);
  },
};
