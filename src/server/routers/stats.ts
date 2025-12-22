import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { protectedProcedure, router } from '../trpc';
import { db } from '@/db';
import { teams, players, matches, matchStats } from '@/db/schema';
import { eq, and, or } from 'drizzle-orm';
import { hasActiveSubscription } from '@/lib/subscription-check';

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
 * Stats router for fetching statistics.
 */
export const statsRouter = router({
  /**
   * Gets team statistics.
   *
   * Protected endpoint - requires subscription.
   *
   * @param input - Team ID and League ID
   * @returns Team statistics
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

      const [team] = await db
        .select()
        .from(teams)
        .where(eq(teams.id, input.teamId))
        .limit(1);

      if (!team) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Team not found',
        });
      }

      // Get match stats for this team (home or away)
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

      // Get match stats for these matches
      const matchIds = teamMatches.map((m) => m.id);
      const statsRecords =
        matchIds.length > 0
          ? await db
              .select()
              .from(matchStats)
              .where(or(...matchIds.map((id) => eq(matchStats.matchId, id))))
          : [];

      // Calculate aggregated stats
      let totalGoals = 0;
      let totalShots = 0;
      let totalShotsOnTarget = 0;
      let wins = 0;
      let draws = 0;
      let losses = 0;

      for (const match of teamMatches) {
        const stats = statsRecords.find((s) => s.matchId === match.id);
        const isHome = match.homeTeamId === input.teamId;

        if (match.status === 'finished') {
          const homeScore = match.homeScore ?? 0;
          const awayScore = match.awayScore ?? 0;

          if (isHome) {
            totalGoals += homeScore;
            if (homeScore > awayScore) wins++;
            else if (homeScore === awayScore) draws++;
            else losses++;

            if (stats) {
              totalShots += stats.homeShots ?? 0;
              totalShotsOnTarget += stats.homeShotsOnTarget ?? 0;
            }
          } else {
            totalGoals += awayScore;
            if (awayScore > homeScore) wins++;
            else if (awayScore === homeScore) draws++;
            else losses++;

            if (stats) {
              totalShots += stats.awayShots ?? 0;
              totalShotsOnTarget += stats.awayShotsOnTarget ?? 0;
            }
          }
        }
      }

      return {
        team,
        matches: teamMatches.length,
        wins,
        draws,
        losses,
        totalGoals,
        totalShots,
        totalShotsOnTarget,
        goalsPerMatch:
          teamMatches.length > 0 ? totalGoals / teamMatches.length : 0,
      };
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
