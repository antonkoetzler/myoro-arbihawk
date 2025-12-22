/**
 * Centralized route definitions for type-safe routing.
 *
 * Use these constants instead of hard-coded strings throughout the application.
 * Next.js typedRoutes will validate these at compile time.
 */

export const routes = {
  /** Home page (login/signup) */
  home: '/',
  /** User subscriptions page */
  subscriptions: '/subscriptions',
  /** Leagues browsing page */
  leagues: '/leagues',
  /** Matches listing page */
  matches: '/matches',
  /** Stats page */
  stats: '/stats',
  /**
   * Match detail page.
   *
   * @param matchId - UUID of the match
   */
  match: (matchId: string) => `/matches/${matchId}`,
  /**
   * League standings page.
   *
   * @param leagueId - UUID of the league
   */
  standings: (leagueId: string) => `/standings/${leagueId}`,
  /**
   * Subscription checkout page.
   *
   * @param leagueId - UUID of the league to subscribe to
   */
  subscribe: (leagueId: string) => `/subscribe/${leagueId}`,
} as const;

/**
 * Type helper for route paths.
 */
export type RoutePath =
  | (typeof routes)[keyof typeof routes]
  | ReturnType<typeof routes.match>
  | ReturnType<typeof routes.standings>
  | ReturnType<typeof routes.subscribe>;
