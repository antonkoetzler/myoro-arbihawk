import { NextResponse } from 'next/server';
import { db } from '@/db';
import { leagues, teams, matches } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { getLeagues, getTeams, getFixtures } from '@/lib/api-football';
import { isCacheStale, getCacheInterval } from '@/lib/cache';

/**
 * Background sync job endpoint.
 *
 * Syncs data from API-Football to database.
 * Can be called via cron job or manually.
 *
 * TODO: Add authentication/authorization for production
 */
export async function POST(req: Request) {
  try {
    const authHeader = req.headers.get('authorization');
    const expectedToken = process.env.SYNC_JOB_TOKEN;

    if (expectedToken && authHeader !== `Bearer ${expectedToken}`) {
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
        const leagueData = apiLeague.league || apiLeague;
        const [existing] = await db
          .select()
          .from(leagues)
          .where(eq(leagues.apiLeagueId, leagueData.id))
          .limit(1);

        if (!existing) {
          await db.insert(leagues).values({
            name: leagueData.name,
            country: leagueData.country || 'Unknown',
            apiLeagueId: leagueData.id,
            logoUrl: leagueData.logo,
            isActive: true,
          });
          syncResults.leagues++;
        }
      }
    } catch (error) {
      console.error('Error syncing leagues:', error);
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
          const teamData = apiTeam.team || apiTeam;
          const [existing] = await db
            .select()
            .from(teams)
            .where(eq(teams.apiTeamId, teamData.id))
            .limit(1);

          if (!existing) {
            await db.insert(teams).values({
              leagueId: league.id,
              name: teamData.name,
              logoUrl: teamData.logo,
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
          const fixture = apiFixture.fixture || apiFixture;
          const homeTeam = apiFixture.teams?.home || {};
          const awayTeam = apiFixture.teams?.away || {};

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

          const [existing] = await db
            .select()
            .from(matches)
            .where(eq(matches.apiMatchId, fixture.id))
            .limit(1);

          if (!existing) {
            await db.insert(matches).values({
              leagueId: league.id,
              homeTeamId: homeTeamRecord.id,
              awayTeamId: awayTeamRecord.id,
              date: new Date(fixture.date),
              status:
                fixture.status?.short === 'FT'
                  ? 'finished'
                  : fixture.status?.short === 'LIVE'
                    ? 'live'
                    : 'scheduled',
              homeScore: fixture.goals?.home,
              awayScore: fixture.goals?.away,
              apiMatchId: fixture.id,
              rawData: apiFixture,
            });
            syncResults.matches++;
          }
        }
      } catch (error) {
        console.error(`Error syncing league ${league.id}:`, error);
      }
    }

    return NextResponse.json({
      success: true,
      results: syncResults,
    });
  } catch (error) {
    console.error('Sync job error:', error);
    return NextResponse.json(
      {
        error: 'Sync failed',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
