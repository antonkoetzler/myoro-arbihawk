import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { protectedProcedure, publicProcedure, router } from '../trpc';
import { db } from '@/db';
import { leagues } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { hasActiveSubscription } from '@/lib/subscription-check';

/**
 * Zod schema for getting leagues.
 */
const getLeaguesSchema = z.object({
  country: z.string().optional(),
  activeOnly: z.boolean().optional().default(true),
});

/**
 * Zod schema for getting league by ID.
 */
const getLeagueSchema = z.object({
  leagueId: z.string().uuid(),
});

/**
 * Leagues router for browsing and managing league subscriptions.
 */
export const leaguesRouter = router({
  /**
   * Gets all available leagues.
   *
   * Public endpoint - anyone can browse leagues.
   *
   * @param input - Optional filters (country, activeOnly)
   * @returns Array of league objects
   */
  getAll: publicProcedure
    .input(getLeaguesSchema.optional())
    .query(async ({ input }) => {
      const query = db.select().from(leagues);

      if (input?.activeOnly) {
        query.where(eq(leagues.isActive, true));
      }

      // TODO: Add country filter if needed

      return query;
    }),

  /**
   * Gets a specific league by ID.
   *
   * Public endpoint - anyone can view league details.
   *
   * @param input - League ID
   * @returns League object
   * @throws {TRPCError} NOT_FOUND if league doesn't exist
   */
  getById: publicProcedure.input(getLeagueSchema).query(async ({ input }) => {
    const [league] = await db
      .select()
      .from(leagues)
      .where(eq(leagues.id, input.leagueId))
      .limit(1);

    if (!league) {
      throw new TRPCError({
        code: 'NOT_FOUND',
        message: 'League not found',
      });
    }

    return league;
  }),

  /**
   * Checks if user has active subscription to a league.
   *
   * Protected endpoint - requires authentication.
   *
   * @param input - League ID
   * @returns Object with subscription status
   */
  checkSubscription: protectedProcedure
    .input(getLeagueSchema)
    .query(async ({ input, ctx }) => {
      if (!ctx.userId) {
        throw new TRPCError({ code: 'UNAUTHORIZED' });
      }

      const hasAccess = await hasActiveSubscription(ctx.userId, input.leagueId);

      return {
        hasAccess,
        leagueId: input.leagueId,
      };
    }),
});
