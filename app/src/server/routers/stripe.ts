import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { protectedProcedure, router } from '../trpc';
import { createCheckoutSession } from '@/lib/stripe';
import { db } from '@/db';
import { leagues, users } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { env } from '@/lib/env';

/**
 * Zod schema for creating checkout session.
 */
const createCheckoutSchema = z.object({
  leagueId: z.string().uuid(),
});

/**
 * Stripe router for handling subscription checkout.
 */
export const stripeRouter = router({
  /**
   * Creates a Stripe checkout session for league subscription.
   *
   * @param input - Object containing leagueId
   * @returns Checkout session URL
   * @throws {TRPCError} NOT_FOUND if league doesn't exist
   * @throws {TRPCError} BAD_REQUEST if league is not active
   */
  createCheckout: protectedProcedure
    .input(createCheckoutSchema)
    .mutation(async ({ input, ctx }) => {
      if (!ctx.userId) {
        throw new TRPCError({ code: 'UNAUTHORIZED' });
      }

      // Get league from database
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

      if (!league.isActive) {
        throw new TRPCError({
          code: 'BAD_REQUEST',
          message: 'League is not available for subscription',
        });
      }

      // Get user email from database
      const [user] = await db
        .select()
        .from(users)
        .where(eq(users.id, ctx.userId))
        .limit(1);

      if (!user) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'User not found',
        });
      }

      // Get Stripe price ID from environment or league configuration
      // In production, you might want to store price IDs per league in the database
      const priceId = env.STRIPE_PRICE_ID || '';

      if (!priceId) {
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Stripe price not configured',
        });
      }

      const session = await createCheckoutSession(
        ctx.userId,
        user.email,
        league.id,
        league.name,
        priceId
      );

      return {
        url: session.url,
      };
    }),
});
