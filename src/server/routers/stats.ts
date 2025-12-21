import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { protectedProcedure, router } from '../trpc';
import { db } from '@/db';
import { teams, players, matches } from '@/db/schema';
import { eq, and } from 'drizzle-orm';
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

      // Get match stats for this team
      const teamMatches = await db
        .select()
        .from(matches)
        .where(
          and(
            eq(matches.leagueId, input.leagueId)
            // Match where team is home or away
            // This is simplified - in production, use OR condition
          )
        );

      // TODO: Calculate aggregated stats from match data
      return {
        team,
        matches: teamMatches.length,
        // Add more stats as needed
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

      // TODO: Calculate player stats from match data
      return {
        player,
        // Add stats as needed
      };
    }),
});
