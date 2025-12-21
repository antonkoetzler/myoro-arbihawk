import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { protectedProcedure, router } from '../trpc';
import { db } from '@/db';
import { matches, teams, matchStats } from '@/db/schema';
import { eq, desc } from 'drizzle-orm';
import { hasActiveSubscription } from '@/lib/subscription-check';

/**
 * Zod schema for getting matches.
 */
const getMatchesSchema = z.object({
  leagueId: z.string().uuid(),
  status: z.enum(['scheduled', 'live', 'finished']).optional(),
});

/**
 * Zod schema for getting match by ID.
 */
const getMatchSchema = z.object({
  matchId: z.string().uuid(),
});

/**
 * Matches router for fetching match data.
 */
export const matchesRouter = router({
  /**
   * Gets matches for a specific league.
   *
   * Protected endpoint - requires subscription.
   *
   * @param input - League ID and optional status filter
   * @returns Array of match objects
   * @throws {TRPCError} UNAUTHORIZED if user doesn't have subscription
   */
  getByLeague: protectedProcedure
    .input(getMatchesSchema)
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

      let query = db
        .select()
        .from(matches)
        .where(eq(matches.leagueId, input.leagueId));

      if (input.status) {
        query = query.where(eq(matches.status, input.status));
      }

      return query.orderBy(desc(matches.date));
    }),

  /**
   * Gets a specific match by ID.
   *
   * Protected endpoint - requires subscription.
   *
   * @param input - Match ID
   * @returns Match object with team and stats information
   * @throws {TRPCError} UNAUTHORIZED if user doesn't have subscription
   */
  getById: protectedProcedure
    .input(getMatchSchema)
    .query(async ({ input, ctx }) => {
      if (!ctx.userId) {
        throw new TRPCError({ code: 'UNAUTHORIZED' });
      }

      const [match] = await db
        .select()
        .from(matches)
        .where(eq(matches.id, input.matchId))
        .limit(1);

      if (!match) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Match not found',
        });
      }

      // Check subscription
      const hasAccess = await hasActiveSubscription(ctx.userId, match.leagueId);
      if (!hasAccess) {
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Subscription required',
        });
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
        homeTeam,
        awayTeam,
        stats: stats || null,
      };
    }),

  /**
   * Gets live matches for subscribed leagues.
   *
   * Protected endpoint - requires at least one subscription.
   *
   * @returns Array of live match objects
   */
  getLive: protectedProcedure.query(async ({ ctx }) => {
    if (!ctx.userId) {
      throw new TRPCError({ code: 'UNAUTHORIZED' });
    }

    // TODO: Filter by user's subscribed leagues
    // For now, return all live matches
    return db
      .select()
      .from(matches)
      .where(eq(matches.status, 'live'))
      .orderBy(desc(matches.date));
  }),
});
