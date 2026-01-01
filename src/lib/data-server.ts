import { db } from '@/db';
import { matches, teams, matchStats, leagues } from '@/db/schema';
import { eq, and, desc } from 'drizzle-orm';
import { hasActiveSubscription } from '@/lib/subscription-check';
import { getFixtures } from '@/lib/api-football';
import type { Match, Team } from '@/db/schema';
import { logger } from '@/lib/logger';

/**
 * Server-side data fetching utilities.
 *
 * These functions fetch data directly from the database for use in server components.
 * They replace tRPC queries for better SSR performance.
 */

/**
 * Syncs finished matches from RapidAPI for a specific league.
 * Only stores finished matches in the database.
 *
 * @param leagueId - League UUID
 * @param apiLeagueId - API-Football league ID
 */
async function syncFinishedMatchesForLeague(
  leagueId: string,
  apiLeagueId: number
) {
  const { env } = await import('@/lib/env');

  // Check if RapidAPI is configured
  if (!env.RAPIDAPI_KEY) {
    logger.warn(
      '[syncFinishedMatchesForLeague]: RAPIDAPI_KEY not configured. Skipping match sync from RapidAPI.'
    );
    return;
  }

  try {
    const currentSeason = new Date().getFullYear();
    const apiFixtures = await getFixtures(apiLeagueId, currentSeason);

    if (!apiFixtures || apiFixtures.length === 0) {
      return;
    }

    let finishedCount = 0;

    for (const apiFixture of apiFixtures) {
      type ApiFixture = {
        fixture?: {
          id: number;
          date: string;
          status?: { short?: string };
          goals?: { home?: number; away?: number };
        };
        teams?: {
          home?: { id: number };
          away?: { id: number };
        };
      };

      const fixtureData = apiFixture as unknown as ApiFixture;
      const fixture =
        fixtureData.fixture || (apiFixture as unknown as ApiFixture['fixture']);
      const homeTeam = fixtureData.teams?.home;
      const awayTeam = fixtureData.teams?.away;

      if (!fixture || !homeTeam?.id || !awayTeam?.id) {
        continue;
      }

      // Only store finished matches
      const isFinished = fixture.status?.short === 'FT';
      if (!isFinished) {
        continue;
      }

      // Find team IDs
      const [homeTeamRecord] = await db
        .select()
        .from(teams)
        .where(eq(teams.apiTeamId, homeTeam.id))
        .limit(1);

      const [awayTeamRecord] = await db
        .select()
        .from(teams)
        .where(eq(teams.apiTeamId, awayTeam.id))
        .limit(1);

      if (!homeTeamRecord || !awayTeamRecord) {
        continue; // Skip if teams not found
      }

      // Check if match already exists
      const [existing] = await db
        .select()
        .from(matches)
        .where(eq(matches.apiMatchId, fixture.id))
        .limit(1);

      if (existing) {
        // Update existing finished match
        await db
          .update(matches)
          .set({
            status: 'finished',
            homeScore: fixture.goals?.home,
            awayScore: fixture.goals?.away,
            updatedAt: new Date(),
          })
          .where(eq(matches.id, existing.id));
        finishedCount++;
      } else {
        // Insert new finished match
        await db.insert(matches).values({
          leagueId,
          homeTeamId: homeTeamRecord.id,
          awayTeamId: awayTeamRecord.id,
          date: new Date(fixture.date),
          status: 'finished',
          homeScore: fixture.goals?.home,
          awayScore: fixture.goals?.away,
          apiMatchId: fixture.id,
          rawData: apiFixture,
        });
        finishedCount++;
      }
    }

    if (finishedCount > 0) {
      logger.log(
        `[syncFinishedMatchesForLeague]: ✅ Synced ${finishedCount} finished matches for league ${leagueId}`
      );
    }
  } catch (error) {
    // Log error but don't throw - we can still show matches from DB
    const errorMessage = error instanceof Error ? error.message : String(error);
    logger.error(
      `[syncFinishedMatchesForLeague]: ❌ Failed to sync finished matches for league ${leagueId}:`,
      errorMessage
    );
  }
}

/**
 * Fetches live and scheduled matches from RapidAPI and converts them to Match format.
 *
 * @param leagueId - League UUID
 * @param apiLeagueId - API-Football league ID
 * @param statusFilter - Optional status filter ('live' or 'scheduled')
 * @returns Array of Match objects
 */
async function fetchLiveAndScheduledMatchesFromAPI(
  leagueId: string,
  apiLeagueId: number,
  statusFilter?: 'live' | 'scheduled'
): Promise<Match[]> {
  const { env } = await import('@/lib/env');

  // Check if RapidAPI is configured
  if (!env.RAPIDAPI_KEY) {
    return [];
  }

  try {
    const currentSeason = new Date().getFullYear();
    const apiFixtures = await getFixtures(apiLeagueId, currentSeason);

    if (!apiFixtures || apiFixtures.length === 0) {
      logger.warn(
        `[fetchLiveAndScheduledMatchesFromAPI]: No fixtures found for league ${apiLeagueId} in season ${currentSeason}`
      );
      return [];
    }

    const matches: Match[] = [];

    for (const apiFixture of apiFixtures) {
      type ApiFixture = {
        fixture?: {
          id: number;
          date: string;
          status?: { short?: string };
          goals?: { home?: number; away?: number };
        };
        teams?: {
          home?: { id: number };
          away?: { id: number };
        };
      };

      const fixtureData = apiFixture as unknown as ApiFixture;
      const fixture =
        fixtureData.fixture || (apiFixture as unknown as ApiFixture['fixture']);
      const homeTeam = fixtureData.teams?.home;
      const awayTeam = fixtureData.teams?.away;

      if (!fixture || !homeTeam?.id || !awayTeam?.id) {
        continue;
      }

      // Determine match status
      const statusShort = fixture.status?.short || '';
      let matchStatus: 'scheduled' | 'live' | 'finished' = 'scheduled';
      if (statusShort === 'FT') {
        matchStatus = 'finished';
      } else if (
        statusShort === 'LIVE' ||
        statusShort === '1H' ||
        statusShort === '2H' ||
        statusShort === 'HT' ||
        statusShort === 'ET' ||
        statusShort === 'PEN'
      ) {
        matchStatus = 'live';
      }

      // Only return live and scheduled matches (not finished)
      if (matchStatus === 'finished') {
        continue;
      }

      // Apply status filter if provided
      if (statusFilter && matchStatus !== statusFilter) {
        continue;
      }

      // Find team IDs
      const [homeTeamRecord] = await db
        .select()
        .from(teams)
        .where(eq(teams.apiTeamId, homeTeam.id))
        .limit(1);

      const [awayTeamRecord] = await db
        .select()
        .from(teams)
        .where(eq(teams.apiTeamId, awayTeam.id))
        .limit(1);

      if (!homeTeamRecord || !awayTeamRecord) {
        continue; // Skip if teams not found
      }

      // Create a temporary Match object (not stored in DB)
      // We need to generate a temporary UUID for the match
      const tempMatch: Match = {
        id: `temp-${fixture.id}`, // Temporary ID
        leagueId,
        homeTeamId: homeTeamRecord.id,
        awayTeamId: awayTeamRecord.id,
        date: new Date(fixture.date),
        status: matchStatus,
        homeScore: fixture.goals?.home ?? null,
        awayScore: fixture.goals?.away ?? null,
        apiMatchId: fixture.id,
        rawData: apiFixture as Record<string, unknown>,
        createdAt: new Date(fixture.date),
        updatedAt: new Date(),
      };

      matches.push(tempMatch);
    }

    return matches.sort((a, b) => b.date.getTime() - a.date.getTime());
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    logger.error(
      `[fetchLiveAndScheduledMatchesFromAPI]: ❌ Failed to fetch live/scheduled matches from RapidAPI:`,
      errorMessage
    );
    return [];
  }
}

/**
 * Gets matches for a league (server-side).
 *
 * - Live and scheduled matches: Fetched directly from RapidAPI (not stored in DB)
 * - Finished matches: Fetched from database (stored after completion)
 *
 * @param userId - Authenticated user ID
 * @param leagueId - League ID
 * @param status - Optional status filter
 * @returns Array of matches
 */
export async function getMatchesByLeague(
  userId: string,
  leagueId: string,
  status?: 'scheduled' | 'live' | 'finished'
): Promise<Match[]> {
  // Check subscription
  const hasAccess = await hasActiveSubscription(userId, leagueId);
  if (!hasAccess) {
    throw new Error('Subscription required');
  }

  // Get league to find API league ID
  const [league] = await db
    .select()
    .from(leagues)
    .where(eq(leagues.id, leagueId))
    .limit(1);

  if (!league) {
    throw new Error('League not found');
  }

  // Sync finished matches to DB (background operation, don't wait for errors)
  syncFinishedMatchesForLeague(leagueId, league.apiLeagueId).catch(() => {
    // Silently fail - we can still show matches
  });

  // Determine what to fetch based on status filter
  const wantsFinished = status === 'finished' || status === undefined;
  const wantsLiveOrScheduled =
    status === 'live' || status === 'scheduled' || status === undefined;

  const results: Match[] = [];

  // Fetch live and scheduled matches from RapidAPI
  if (wantsLiveOrScheduled) {
    const liveAndScheduled = await fetchLiveAndScheduledMatchesFromAPI(
      leagueId,
      league.apiLeagueId,
      status === 'live' || status === 'scheduled' ? status : undefined
    );
    results.push(...liveAndScheduled);
  }

  // Fetch finished matches from database
  if (wantsFinished) {
    const finishedMatches = await db
      .select()
      .from(matches)
      .where(
        and(eq(matches.leagueId, leagueId), eq(matches.status, 'finished'))
      )
      .orderBy(desc(matches.date));

    results.push(...finishedMatches);
  }

  // Sort all results by date (newest first)
  return results.sort((a, b) => b.date.getTime() - a.date.getTime());
}

/**
 * Gets a match by ID with teams and stats (server-side).
 *
 * @param userId - Authenticated user ID
 * @param matchId - Match ID
 * @returns Match with teams and stats
 */
export async function getMatchById(userId: string, matchId: string) {
  const [match] = await db
    .select()
    .from(matches)
    .where(eq(matches.id, matchId))
    .limit(1);

  if (!match) {
    return null;
  }

  // Check subscription
  const hasAccess = await hasActiveSubscription(userId, match.leagueId);
  if (!hasAccess) {
    throw new Error('Subscription required');
  }

  // Get teams
  const [homeTeam] = await db
    .select()
    .from(teams)
    .where(eq(teams.id, match.homeTeamId))
    .limit(1);

  const [awayTeam] = await db
    .select()
    .from(teams)
    .where(eq(teams.id, match.awayTeamId))
    .limit(1);

  // Get stats
  const [stats] = await db
    .select()
    .from(matchStats)
    .where(eq(matchStats.matchId, match.id))
    .limit(1);

  return {
    match,
    homeTeam: homeTeam || null,
    awayTeam: awayTeam || null,
    stats: stats || null,
  };
}

/**
 * Gets league standings (server-side).
 *
 * @param userId - Authenticated user ID
 * @param leagueId - League ID
 * @returns Array of team standings
 */
export async function getLeagueStandings(userId: string, leagueId: string) {
  // Check subscription
  const hasAccess = await hasActiveSubscription(userId, leagueId);
  if (!hasAccess) {
    throw new Error('Subscription required');
  }

  const leagueTeams = await db
    .select()
    .from(teams)
    .where(eq(teams.leagueId, leagueId));

  const standingsMap = new Map<
    string,
    {
      team: Team;
      played: number;
      wins: number;
      draws: number;
      losses: number;
      goalsFor: number;
      goalsAgainst: number;
      goalDifference: number;
      points: number;
    }
  >();

  for (const team of leagueTeams) {
    standingsMap.set(team.id, {
      team,
      played: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goalsFor: 0,
      goalsAgainst: 0,
      goalDifference: 0,
      points: 0,
    });
  }

  const finishedMatches = await db
    .select()
    .from(matches)
    .where(and(eq(matches.leagueId, leagueId), eq(matches.status, 'finished')));

  for (const match of finishedMatches) {
    const homeTeamStats = standingsMap.get(match.homeTeamId);
    const awayTeamStats = standingsMap.get(match.awayTeamId);

    if (!homeTeamStats || !awayTeamStats) continue;

    const homeScore = match.homeScore ?? 0;
    const awayScore = match.awayScore ?? 0;

    homeTeamStats.played++;
    awayTeamStats.played++;

    homeTeamStats.goalsFor += homeScore;
    homeTeamStats.goalsAgainst += awayScore;
    awayTeamStats.goalsFor += awayScore;
    awayTeamStats.goalsAgainst += homeScore;

    if (homeScore > awayScore) {
      homeTeamStats.wins++;
      homeTeamStats.points += 3;
      awayTeamStats.losses++;
    } else if (homeScore < awayScore) {
      awayTeamStats.wins++;
      awayTeamStats.points += 3;
      homeTeamStats.losses++;
    } else {
      homeTeamStats.draws++;
      awayTeamStats.draws++;
      homeTeamStats.points += 1;
      awayTeamStats.points += 1;
    }
  }

  const standings = Array.from(standingsMap.values()).map((s) => ({
    ...s,
    goalDifference: s.goalsFor - s.goalsAgainst,
  }));

  return standings.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.goalDifference !== a.goalDifference)
      return b.goalDifference - a.goalDifference;
    return a.team.name.localeCompare(b.team.name);
  });
}
