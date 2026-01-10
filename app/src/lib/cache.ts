/**
 * Caching utilities for API data.
 *
 * Provides helper functions to check cache freshness and determine
 * when data should be refreshed from the API.
 */

/**
 * Cache refresh intervals in milliseconds.
 */
export const CACHE_INTERVALS = {
  /** Matches: refresh every 15 minutes */
  MATCHES: 15 * 60 * 1000,
  /** Standings: refresh daily */
  STANDINGS: 24 * 60 * 60 * 1000,
  /** Teams: refresh weekly */
  TEAMS: 7 * 24 * 60 * 60 * 1000,
  /** Players: refresh weekly */
  PLAYERS: 7 * 24 * 60 * 60 * 1000,
  /** Leagues: refresh weekly */
  LEAGUES: 7 * 24 * 60 * 60 * 1000,
} as const;

/**
 * Checks if cached data is stale and needs refresh.
 *
 * @param lastUpdated - Timestamp when data was last updated
 * @param cacheInterval - Cache interval in milliseconds
 * @returns True if data is stale and needs refresh
 */
export function isCacheStale(
  lastUpdated: Date,
  cacheInterval: number
): boolean {
  const now = new Date();
  const age = now.getTime() - lastUpdated.getTime();
  return age > cacheInterval;
}

/**
 * Gets the appropriate cache interval for a data type.
 *
 * @param dataType - Type of data (matches, standings, teams, etc.)
 * @returns Cache interval in milliseconds
 */
export function getCacheInterval(
  dataType: keyof typeof CACHE_INTERVALS
): number {
  return CACHE_INTERVALS[dataType];
}
