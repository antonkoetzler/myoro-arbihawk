import { NextResponse } from 'next/server';
import { db } from '@/db';
import { leagues, teams, matches } from '@/db/schema';
import { eq } from 'drizzle-orm';
import {
  getLeagues,
  getTeams,
  getFixtures,
  type ApiLeague,
  type ApiTeam,
  type ApiFixture,
} from '@/lib/api-football';
import { isCacheStale, getCacheInterval } from '@/lib/cache';
import { env } from '@/lib/env';
import { logger } from '@/lib/logger';

/**
 * Background sync job endpoint.
 *
 * Syncs data from API-Football to database.
 * Can be called via cron job or manually.
 *
 * Requires SYNC_JOB_TOKEN in environment for authentication.
 */
export async function POST(req: Request) {
  try {
    const authHeader = req.headers.get('authorization');
    const expectedToken = env.SYNC_JOB_TOKEN;

    if (!expectedToken) {
      return NextResponse.json(
        { error: 'Sync job not configured' },
        { status: 500 }
      );
    }

    if (authHeader !== `Bearer ${expectedToken}`) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const syncResults = {
      leagues: 0,
      teams: 0,
      matches: 0,
      players: 0,
      stats: 0,
    };

    // Sync leagues
    try {
      const apiLeagues = await getLeagues();
      for (const apiLeague of apiLeagues) {
        const leagueData =
          (apiLeague.league as ApiLeague | undefined) ?? apiLeague;
        if (!leagueData.id || typeof leagueData.id !== 'number') {
          continue;
        }
        const [existing] = await db
          .select()
          .from(leagues)
          .where(eq(leagues.apiLeagueId, leagueData.id))
          .limit(1);

        if (!existing) {
          await db.insert(leagues).values({
            name:
              typeof leagueData.name === 'string'
                ? leagueData.name
                : 'Unknown League',
            country:
              typeof leagueData.country === 'string'
                ? leagueData.country
                : 'Unknown',
            apiLeagueId: leagueData.id,
            logoUrl:
              typeof leagueData.logo === 'string' ? leagueData.logo : undefined,
            isActive: true,
          });
          syncResults.leagues++;
        }
      }
    } catch (error) {
      logger.error('[POST /api/sync]: Error syncing leagues:', error);
    }

    // Sync teams and matches for active leagues
    const activeLeagues = await db
      .select()
      .from(leagues)
      .where(eq(leagues.isActive, true));

    const currentSeason = new Date().getFullYear();

    for (const league of activeLeagues) {
      try {
        // Check if league data is stale
        const shouldSync =
          !league.updatedAt ||
          isCacheStale(league.updatedAt, getCacheInterval('TEAMS'));

        if (!shouldSync) {
          continue;
        }

        // Sync teams
        const apiTeams = await getTeams(league.apiLeagueId, currentSeason);
        for (const apiTeam of apiTeams) {
          const teamData = (apiTeam.team as ApiTeam | undefined) ?? apiTeam;
          if (!teamData.id || typeof teamData.id !== 'number') {
            continue;
          }
          const [existing] = await db
            .select()
            .from(teams)
            .where(eq(teams.apiTeamId, teamData.id))
            .limit(1);

          if (!existing) {
            await db.insert(teams).values({
              leagueId: league.id,
              name:
                typeof teamData.name === 'string'
                  ? teamData.name
                  : 'Unknown Team',
              logoUrl:
                typeof teamData.logo === 'string' ? teamData.logo : undefined,
              apiTeamId: teamData.id,
              rawData: teamData,
            });
            syncResults.teams++;
          }
        }

        // Sync fixtures (matches)
        const apiFixtures = await getFixtures(
          league.apiLeagueId,
          currentSeason
        );
        for (const apiFixture of apiFixtures) {
          const fixture =
            (apiFixture.fixture as ApiFixture['fixture'] | undefined) ??
            apiFixture;
          if (!fixture || typeof fixture !== 'object') {
            continue;
          }
          const fixtureId =
            'id' in fixture && typeof fixture.id === 'number'
              ? fixture.id
              : undefined;
          if (!fixtureId) {
            continue;
          }
          const homeTeam = apiFixture.teams?.home;
          const awayTeam = apiFixture.teams?.away;
          const homeTeamId =
            homeTeam && typeof homeTeam === 'object' && 'id' in homeTeam
              ? typeof homeTeam.id === 'number'
                ? homeTeam.id
                : undefined
              : undefined;
          const awayTeamId =
            awayTeam && typeof awayTeam === 'object' && 'id' in awayTeam
              ? typeof awayTeam.id === 'number'
                ? awayTeam.id
                : undefined
              : undefined;

          if (!homeTeamId || !awayTeamId) {
            continue; // Skip if team IDs not found
          }

          // Find team IDs
          const [homeTeamRecord] = await db
            .select()
            .from(teams)
            .where(eq(teams.apiTeamId, homeTeamId))
            .limit(1);

          const [awayTeamRecord] = await db
            .select()
            .from(teams)
            .where(eq(teams.apiTeamId, awayTeamId))
            .limit(1);

          if (!homeTeamRecord || !awayTeamRecord) {
            continue; // Skip if teams not found
          }

          const [existing] = await db
            .select()
            .from(matches)
            .where(eq(matches.apiMatchId, fixtureId))
            .limit(1);

          if (!existing) {
            const fixtureDate =
              'date' in fixture && typeof fixture.date === 'string'
                ? fixture.date
                : new Date().toISOString();
            const status =
              'status' in fixture &&
              fixture.status &&
              typeof fixture.status === 'object' &&
              'short' in fixture.status &&
              typeof fixture.status.short === 'string'
                ? fixture.status.short === 'FT'
                  ? 'finished'
                  : fixture.status.short === 'LIVE'
                    ? 'live'
                    : 'scheduled'
                : 'scheduled';
            const goals =
              'goals' in fixture &&
              fixture.goals &&
              typeof fixture.goals === 'object'
                ? fixture.goals
                : undefined;
            const homeScore =
              goals && 'home' in goals && typeof goals.home === 'number'
                ? goals.home
                : undefined;
            const awayScore =
              goals && 'away' in goals && typeof goals.away === 'number'
                ? goals.away
                : undefined;

            await db.insert(matches).values({
              leagueId: league.id,
              homeTeamId: homeTeamRecord.id,
              awayTeamId: awayTeamRecord.id,
              date: new Date(fixtureDate),
              status,
              homeScore,
              awayScore,
              apiMatchId: fixtureId,
              rawData: apiFixture,
            });
            syncResults.matches++;
          }
        }
      } catch (error) {
        logger.error(
          `[POST /api/sync]: Error syncing league ${league.id}:`,
          error
        );
      }
    }

    return NextResponse.json({
      success: true,
      results: syncResults,
    });
  } catch (error) {
    logger.error('[POST /api/sync]: Sync job error:', error);
    return NextResponse.json(
      {
        error: 'Sync failed',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
