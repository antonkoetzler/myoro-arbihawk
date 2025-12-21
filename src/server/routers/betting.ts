import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { protectedProcedure, router } from '../trpc';
import { db } from '@/db';
import { bettingRecommendations, matches } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { hasActiveSubscription } from '@/lib/subscription-check';
import { calculateBettingRecommendations } from '@/lib/betting-engine';

/**
 * Zod schema for getting betting recommendations.
 */
const getRecommendationsSchema = z.object({
  matchId: z.string().uuid(),
});

/**
 * Betting router for fetching betting recommendations.
 */
export const bettingRouter = router({
  /**
   * Gets betting recommendations for a match.
   *
   * Protected endpoint - requires subscription.
   *
   * @param input - Match ID
   * @returns Array of betting recommendations
   * @throws {TRPCError} UNAUTHORIZED if user doesn't have subscription
   */
  getRecommendations: protectedProcedure
    .input(getRecommendationsSchema)
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

      // Get existing recommendations or calculate new ones
      const existing = await db
        .select()
        .from(bettingRecommendations)
        .where(eq(bettingRecommendations.matchId, input.matchId));

      if (existing.length > 0) {
        return existing;
      }

      // Calculate new recommendations
      const recommendations = await calculateBettingRecommendations(
        input.matchId
      );
      return recommendations;
    }),
});
