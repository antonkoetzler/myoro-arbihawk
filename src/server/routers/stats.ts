import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { protectedProcedure, router } from '../trpc';
import { db } from '@/db';
import { teams, players, matches, matchStats, leagues } from '@/db/schema';
import { eq, and, or, desc } from 'drizzle-orm';
import { hasActiveSubscription } from '@/lib/subscription-check';
import { logger } from '@/lib/logger';

/**
 * Zod schema for getting team stats.
 */
const getTeamStatsSchema = z.object({
  teamId: z.string().uuid(),
  leagueId: z.string().uuid(),
});

/**
 * Zod schema for getting player stats.
 */
const getPlayerStatsSchema = z.object({
  playerId: z.string().uuid(),
  teamId: z.string().uuid(),
  leagueId: z.string().uuid(),
});

/**
 * Zod schema for getting league standings.
 */
const getStandingsSchema = z.object({
  leagueId: z.string().uuid(),
});

/**
 * Zod schema for getting teams in a league.
 */
const getTeamsSchema = z.object({
  leagueId: z.string().uuid(),
});

/**
 * Calculates comprehensive betting statistics from database matches.
 *
 * @param finishedMatches - Array of finished matches
 * @param statsRecords - Array of match statistics
 * @param teamId - Team ID to calculate stats for
 * @param team - Team object
 * @param teamMap - Map of team IDs to team names for opponent lookup
 * @returns Comprehensive team statistics
 */
function calculateStatsFromDatabase(
  finishedMatches: (typeof matches.$inferSelect)[],
  statsRecords: (typeof matchStats.$inferSelect)[],
  teamId: string,
  team: typeof teams.$inferSelect,
  teamMap: Map<string, string>
) {
  let totalGoals = 0;
  let totalGoalsConceded = 0;
  let totalShots = 0;
  let totalShotsOnTarget = 0;
  let wins = 0;
  let draws = 0;
  let losses = 0;

  // Home and away splits
  let homeGoalsScored = 0;
  let homeGoalsConceded = 0;
  let homeWins = 0;
  let homeDraws = 0;
  let homeLosses = 0;
  let homeMatches = 0;

  let awayGoalsScored = 0;
  let awayGoalsConceded = 0;
  let awayWins = 0;
  let awayDraws = 0;
  let awayLosses = 0;
  let awayMatches = 0;

  // Betting metrics
  let bttsCount = 0; // Both teams to score
  let over25Count = 0; // Over 2.5 goals
  let over15Count = 0; // Over 1.5 goals
  let under25Count = 0; // Under 2.5 goals
  let cleanSheets = 0;

  // Recent form (last 5 matches)
  const recentForm: Array<{
    date: Date;
    opponent: string;
    result: 'W' | 'D' | 'L';
    score: string;
  }> = [];

  for (const match of finishedMatches) {
    const stats = statsRecords.find((s) => s.matchId === match.id);
    const isHome = match.homeTeamId === teamId;
    const homeScore = match.homeScore ?? 0;
    const awayScore = match.awayScore ?? 0;

    if (isHome) {
      totalGoals += homeScore;
      totalGoalsConceded += awayScore;
      homeGoalsScored += homeScore;
      homeGoalsConceded += awayScore;
      homeMatches++;

      if (homeScore > awayScore) {
        wins++;
        homeWins++;
      } else if (homeScore === awayScore) {
        draws++;
        homeDraws++;
      } else {
        losses++;
        homeLosses++;
      }

      if (stats) {
        totalShots += stats.homeShots ?? 0;
        totalShotsOnTarget += stats.homeShotsOnTarget ?? 0;
      }

      if (awayScore === 0) cleanSheets++;
    } else {
      totalGoals += awayScore;
      totalGoalsConceded += homeScore;
      awayGoalsScored += awayScore;
      awayGoalsConceded += homeScore;
      awayMatches++;

      if (awayScore > homeScore) {
        wins++;
        awayWins++;
      } else if (awayScore === homeScore) {
        draws++;
        awayDraws++;
      } else {
        losses++;
        awayLosses++;
      }

      if (stats) {
        totalShots += stats.awayShots ?? 0;
        totalShotsOnTarget += stats.awayShotsOnTarget ?? 0;
      }

      if (homeScore === 0) cleanSheets++;
    }

    // Betting metrics
    const totalGoalsInMatch = homeScore + awayScore;
    if (homeScore > 0 && awayScore > 0) bttsCount++;
    if (totalGoalsInMatch > 2.5) over25Count++;
    if (totalGoalsInMatch > 1.5) over15Count++;
    if (totalGoalsInMatch < 2.5) under25Count++;
  }

  // Calculate recent form (last 5 matches)
  const last5Matches = finishedMatches.slice(0, 5);
  for (const match of last5Matches) {
    const isHome = match.homeTeamId === teamId;
    const homeScore = match.homeScore ?? 0;
    const awayScore = match.awayScore ?? 0;
    const opponentId = isHome ? match.awayTeamId : match.homeTeamId;
    const opponentName =
      teamMap.get(opponentId) || `Team ${opponentId.slice(0, 8)}`;

    let result: 'W' | 'D' | 'L';
    if (isHome) {
      if (homeScore > awayScore) result = 'W';
      else if (homeScore === awayScore) result = 'D';
      else result = 'L';
    } else {
      if (awayScore > homeScore) result = 'W';
      else if (awayScore === homeScore) result = 'D';
      else result = 'L';
    }

    recentForm.push({
      date: match.date,
      opponent: opponentName,
      result,
      score: `${isHome ? homeScore : awayScore}-${isHome ? awayScore : homeScore}`,
    });
  }

  const totalMatches = finishedMatches.length;
  const finishedCount = totalMatches;

  return {
    team,
    matches: totalMatches,
    wins,
    draws,
    losses,
    totalGoals,
    totalShots,
    totalShotsOnTarget,
    goalsPerMatch: finishedCount > 0 ? totalGoals / finishedCount : 0,
    goalsConceded: totalGoalsConceded,
    goalsConcededPerMatch:
      finishedCount > 0 ? totalGoalsConceded / finishedCount : 0,
    homeStats: {
      goalsScored: homeGoalsScored,
      goalsConceded: homeGoalsConceded,
      wins: homeWins,
      draws: homeDraws,
      losses: homeLosses,
      matches: homeMatches,
    },
    awayStats: {
      goalsScored: awayGoalsScored,
      goalsConceded: awayGoalsConceded,
      wins: awayWins,
      draws: awayDraws,
      losses: awayLosses,
      matches: awayMatches,
    },
    bttsPercentage: finishedCount > 0 ? (bttsCount / finishedCount) * 100 : 0,
    over25Percentage:
      finishedCount > 0 ? (over25Count / finishedCount) * 100 : 0,
    over15Percentage:
      finishedCount > 0 ? (over15Count / finishedCount) * 100 : 0,
    under25Percentage:
      finishedCount > 0 ? (under25Count / finishedCount) * 100 : 0,
    cleanSheets,
    recentForm,
    winPercentage: finishedCount > 0 ? (wins / finishedCount) * 100 : 0,
    drawPercentage: finishedCount > 0 ? (draws / finishedCount) * 100 : 0,
    lossPercentage: finishedCount > 0 ? (losses / finishedCount) * 100 : 0,
  };
}

/**
 * Stats router for fetching statistics.
 */
export const statsRouter = router({
  /**
   * Gets all teams in a league.
   *
   * Protected endpoint - requires subscription.
   *
   * @param input - League ID
   * @returns Array of teams
   * @throws {TRPCError} UNAUTHORIZED if user doesn't have subscription
   */
  getTeams: protectedProcedure
    .input(getTeamsSchema)
    .query(async ({ input, ctx }) => {
      if (!ctx.userId) {
        throw new TRPCError({ code: 'UNAUTHORIZED' });
      }

      // Check subscription
      const hasAccess = await hasActiveSubscription(ctx.userId, input.leagueId);
      if (!hasAccess) {
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Subscription required',
        });
      }

      const leagueTeams = await db
        .select()
        .from(teams)
        .where(eq(teams.leagueId, input.leagueId));

      return leagueTeams;
    }),

  /**
   * Gets team statistics with betting-focused metrics.
   *
   * Protected endpoint - requires subscription.
   *
   * Tries to fetch from API-Football MCP first, falls back to database calculations.
   *
   * @param input - Team ID and League ID
   * @returns Team statistics with betting metrics
   * @throws {TRPCError} UNAUTHORIZED if user doesn't have subscription
   */
  getTeamStats: protectedProcedure
    .input(getTeamStatsSchema)
    .query(async ({ input, ctx }) => {
      if (!ctx.userId) {
        throw new TRPCError({ code: 'UNAUTHORIZED' });
      }

      // Check subscription
      const hasAccess = await hasActiveSubscription(ctx.userId, input.leagueId);
      if (!hasAccess) {
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Subscription required',
        });
      }

      // Get team and league with API IDs
      const [teamWithLeague] = await db
        .select({
          team: teams,
          league: leagues,
        })
        .from(teams)
        .innerJoin(leagues, eq(teams.leagueId, leagues.id))
        .where(eq(teams.id, input.teamId))
        .limit(1);

      if (!teamWithLeague) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Team not found',
        });
      }

      const { team } = teamWithLeague;

      // Get all finished matches for this team
      const finishedMatches = await db
        .select()
        .from(matches)
        .where(
          and(
            eq(matches.leagueId, input.leagueId),
            eq(matches.status, 'finished'),
            or(
              eq(matches.homeTeamId, input.teamId),
              eq(matches.awayTeamId, input.teamId)
            )
          )
        )
        .orderBy(desc(matches.date));

      // Get match stats for these matches
      const matchIds = finishedMatches.map((m) => m.id);
      const statsRecords =
        matchIds.length > 0
          ? await db
              .select()
              .from(matchStats)
              .where(or(...matchIds.map((id) => eq(matchStats.matchId, id))))
          : [];

      // Get all teams for opponent names
      const allTeams = await db.select().from(teams);
      const teamMap = new Map(allTeams.map((t) => [t.id, t.name]));

      // Calculate stats from database
      // Note: API-Football MCP integration would require a separate API route
      // For now, we calculate all stats from database matches
      const dbStats = calculateStatsFromDatabase(
        finishedMatches,
        statsRecords,
        input.teamId,
        team,
        teamMap
      );

      logger.log(
        `[getTeamStats]: Calculated stats for team ${team.id} from ${finishedMatches.length} matches`
      );

      return dbStats;
    }),

  /**
   * Gets player statistics.
   *
   * Protected endpoint - requires subscription.
   *
   * @param input - Player ID, Team ID, and League ID
   * @returns Player statistics
   * @throws {TRPCError} UNAUTHORIZED if user doesn't have subscription
   */
  getPlayerStats: protectedProcedure
    .input(getPlayerStatsSchema)
    .query(async ({ input, ctx }) => {
      if (!ctx.userId) {
        throw new TRPCError({ code: 'UNAUTHORIZED' });
      }

      // Check subscription
      const hasAccess = await hasActiveSubscription(ctx.userId, input.leagueId);
      if (!hasAccess) {
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Subscription required',
        });
      }

      const [player] = await db
        .select()
        .from(players)
        .where(eq(players.id, input.playerId))
        .limit(1);

      if (!player) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Player not found',
        });
      }

      // Get matches for this player's team
      const teamMatches = await db
        .select()
        .from(matches)
        .where(
          and(
            eq(matches.leagueId, input.leagueId),
            or(
              eq(matches.homeTeamId, input.teamId),
              eq(matches.awayTeamId, input.teamId)
            )
          )
        );

      // For now, return basic player info
      // In production, you'd calculate goals, assists, etc. from match events
      return {
        player,
        teamId: input.teamId,
        leagueId: input.leagueId,
        matchesAvailable: teamMatches.length,
        // Additional stats would be calculated from match events/player performance data
      };
    }),

  /**
   * Gets league standings/table.
   *
   * Protected endpoint - requires subscription.
   *
   * @param input - League ID
   * @returns Array of team standings
   * @throws {TRPCError} UNAUTHORIZED if user doesn't have subscription
   */
  getStandings: protectedProcedure
    .input(getStandingsSchema)
    .query(async ({ input, ctx }) => {
      if (!ctx.userId) {
        throw new TRPCError({ code: 'UNAUTHORIZED' });
      }

      // Check subscription
      const hasAccess = await hasActiveSubscription(ctx.userId, input.leagueId);
      if (!hasAccess) {
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Subscription required',
        });
      }

      // Get all teams in the league
      const leagueTeams = await db
        .select()
        .from(teams)
        .where(eq(teams.leagueId, input.leagueId));

      // Get all finished matches for this league
      const finishedMatches = await db
        .select()
        .from(matches)
        .where(
          and(
            eq(matches.leagueId, input.leagueId),
            eq(matches.status, 'finished')
          )
        );

      // Calculate standings for each team
      const standings = leagueTeams.map((team) => {
        let wins = 0;
        let draws = 0;
        let losses = 0;
        let goalsFor = 0;
        let goalsAgainst = 0;

        for (const match of finishedMatches) {
          const isHome = match.homeTeamId === team.id;
          const homeScore = match.homeScore ?? 0;
          const awayScore = match.awayScore ?? 0;

          if (isHome) {
            goalsFor += homeScore;
            goalsAgainst += awayScore;
            if (homeScore > awayScore) wins++;
            else if (homeScore === awayScore) draws++;
            else losses++;
          } else {
            goalsFor += awayScore;
            goalsAgainst += homeScore;
            if (awayScore > homeScore) wins++;
            else if (awayScore === homeScore) draws++;
            else losses++;
          }
        }

        const played = wins + draws + losses;
        const points = wins * 3 + draws;
        const goalDifference = goalsFor - goalsAgainst;

        return {
          teamId: team.id,
          teamName: team.name,
          played,
          wins,
          draws,
          losses,
          goalsFor,
          goalsAgainst,
          goalDifference,
          points,
        };
      });

      // Sort by points (desc), then goal difference (desc), then goals for (desc)
      standings.sort((a, b) => {
        if (b.points !== a.points) return b.points - a.points;
        if (b.goalDifference !== a.goalDifference)
          return b.goalDifference - a.goalDifference;
        return b.goalsFor - a.goalsFor;
      });

      return standings;
    }),
});
