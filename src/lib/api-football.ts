/**
 * API-Football client for RapidAPI.
 *
 * Uses native fetch (no axios) to call API-Football endpoints.
 * Implements rate limiting and error handling.
 */

import { env } from '@/lib/env';

/**
 * API-Football league type.
 * Can be returned directly or nested in a 'league' property.
 */
export type ApiLeague = {
  id: number;
  name: string;
  country: string;
  logo?: string;
  flag?: string;
  season?: number;
  // Allow nested structure from API
  league?: ApiLeague;
  // Allow additional properties
  [key: string]: unknown;
};

/**
 * API-Football team type.
 * Can be returned directly or nested in a 'team' property.
 */
export type ApiTeam = {
  id: number;
  name: string;
  logo?: string;
  code?: string;
  // Allow nested structure from API
  team?: ApiTeam;
  // Allow additional properties
  [key: string]: unknown;
};

/**
 * API-Football fixture/match type.
 */
export type ApiFixture = {
  fixture?: {
    id: number;
    date: string;
    status?: {
      short?: string;
      long?: string;
    };
    goals?: {
      home?: number;
      away?: number;
    };
  };
  teams?: {
    home?: ApiTeam;
    away?: ApiTeam;
  };
  league?: ApiLeague;
  goals?: {
    home?: number;
    away?: number;
  };
  // Allow additional properties from API
  [key: string]: unknown;
};

/**
 * API-Football standings type.
 */
export type ApiStandings = {
  league?: {
    id: number;
    name: string;
    country: string;
    standings?: Array<{
      team: ApiTeam;
      points: number;
      goalsDiff: number;
      group?: string;
      form?: string;
      description?: string;
      all?: {
        played: number;
        win: number;
        draw: number;
        lose: number;
        goals: {
          for: number;
          against: number;
        };
      };
    }>;
  };
  [key: string]: unknown;
};

const RAPIDAPI_KEY = env.RAPIDAPI_KEY || '';
const RAPIDAPI_HOST = env.RAPIDAPI_HOST;
const BASE_URL = `https://${RAPIDAPI_HOST}`;

/**
 * Rate limiting state.
 */
let lastRequestTime = 0;
const MIN_REQUEST_INTERVAL = 100; // 100ms between requests (10 requests/second max)

/**
 * Makes a request to API-Football with rate limiting.
 *
 * @param endpoint - API endpoint path
 * @param params - Query parameters
 * @returns API response data
 * @throws Error if API call fails
 */
async function apiRequest<T>(
  endpoint: string,
  params?: Record<string, string | number>
): Promise<T> {
  if (!RAPIDAPI_KEY) {
    throw new Error('RAPIDAPI_KEY not configured');
  }

  // Rate limiting
  const now = Date.now();
  const timeSinceLastRequest = now - lastRequestTime;
  if (timeSinceLastRequest < MIN_REQUEST_INTERVAL) {
    await new Promise((resolve) =>
      setTimeout(resolve, MIN_REQUEST_INTERVAL - timeSinceLastRequest)
    );
  }
  lastRequestTime = Date.now();

  const url = new URL(`${BASE_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, String(value));
    });
  }

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'X-RapidAPI-Key': RAPIDAPI_KEY,
      'X-RapidAPI-Host': RAPIDAPI_HOST,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `API-Football error: ${response.status} ${response.statusText} - ${errorText}`
    );
  }

  const data = (await response.json()) as { response: T };
  if (!('response' in data)) {
    throw new Error('Invalid API-Football response format');
  }
  return data.response;
}

/**
 * Gets all available leagues.
 *
 * @returns Array of league objects
 */
export async function getLeagues(): Promise<ApiLeague[]> {
  return apiRequest<ApiLeague[]>('/leagues');
}

/**
 * Gets leagues by country.
 *
 * @param country - Country name or code
 * @returns Array of league objects
 */
export async function getLeaguesByCountry(
  country: string
): Promise<ApiLeague[]> {
  return apiRequest<ApiLeague[]>(`/leagues`, { country });
}

/**
 * Gets fixtures (matches) for a specific league.
 *
 * @param leagueId - API-Football league ID
 * @param season - Season year (e.g., 2024)
 * @param round - Optional round name
 * @returns Array of fixture objects
 */
export async function getFixtures(
  leagueId: number,
  season: number,
  round?: string
): Promise<ApiFixture[]> {
  const params: Record<string, string | number> = {
    league: leagueId,
    season,
  };
  if (round) {
    params.round = round;
  }
  return apiRequest<ApiFixture[]>('/fixtures', params);
}

/**
 * Gets live fixtures.
 *
 * @returns Array of live fixture objects
 */
export async function getLiveFixtures(): Promise<ApiFixture[]> {
  return apiRequest<ApiFixture[]>('/fixtures', { live: 'all' });
}

/**
 * Gets fixtures by date.
 *
 * @param date - Date in YYYY-MM-DD format
 * @returns Array of fixture objects
 */
export async function getFixturesByDate(date: string): Promise<ApiFixture[]> {
  return apiRequest<ApiFixture[]>('/fixtures', { date });
}

/**
 * Gets a specific fixture by ID.
 *
 * @param fixtureId - API-Football fixture ID
 * @returns Fixture object or null if not found
 */
export async function getFixture(
  fixtureId: number
): Promise<ApiFixture | null> {
  const results = await apiRequest<ApiFixture[]>('/fixtures', {
    id: fixtureId,
  });
  return results.length > 0 ? (results[0] ?? null) : null;
}

/**
 * Gets teams for a specific league.
 *
 * @param leagueId - API-Football league ID
 * @param season - Season year (e.g., 2024)
 * @returns Array of team objects
 */
export async function getTeams(
  leagueId: number,
  season: number
): Promise<ApiTeam[]> {
  return apiRequest<ApiTeam[]>('/teams', { league: leagueId, season });
}

/**
 * Gets a specific team by ID.
 *
 * @param teamId - API-Football team ID
 * @returns Team object or null if not found
 */
export async function getTeam(teamId: number): Promise<ApiTeam | null> {
  const results = await apiRequest<ApiTeam[]>('/teams', { id: teamId });
  return results.length > 0 ? (results[0] ?? null) : null;
}

/**
 * Gets players for a specific team.
 *
 * @param teamId - API-Football team ID
 * @param _season - Season year (e.g., 2024) - unused but kept for API compatibility
 * @returns Array of player objects
 */
export async function getPlayers(
  teamId: number,
  _season: number
): Promise<Array<{ id: number; name: string; [key: string]: unknown }>> {
  return apiRequest<
    Array<{ id: number; name: string; [key: string]: unknown }>
  >('/players/squads', { team: teamId });
}

/**
 * Gets statistics for a specific fixture.
 *
 * @param fixtureId - API-Football fixture ID
 * @returns Statistics object
 */
export async function getFixtureStatistics(
  fixtureId: number
): Promise<
  Array<{ team: ApiTeam; statistics: Array<{ type: string; value: unknown }> }>
> {
  return apiRequest<
    Array<{
      team: ApiTeam;
      statistics: Array<{ type: string; value: unknown }>;
    }>
  >('/fixtures/statistics', { fixture: fixtureId });
}

/**
 * Gets standings/table for a specific league.
 *
 * @param leagueId - API-Football league ID
 * @param season - Season year (e.g., 2024)
 * @returns Standings object
 */
export async function getStandings(
  leagueId: number,
  season: number
): Promise<ApiStandings[]> {
  return apiRequest<ApiStandings[]>('/standings', { league: leagueId, season });
}
