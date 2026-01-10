import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { protectedProcedure, router } from '../trpc';
import { db } from '@/db';
import { subscriptions } from '@/db/schema';
import { eq, and } from 'drizzle-orm';
import { getUserSubscriptions } from '@/lib/subscription-check';
import { cancelSubscription } from '@/lib/stripe';

/**
 * Subscriptions router for managing user subscriptions.
 */
export const subscriptionsRouter = router({
  /**
   * Gets all active subscriptions for the current user.
   *
   * @returns Array of subscription objects with league information
   */
  getMySubscriptions: protectedProcedure.query(async ({ ctx }) => {
    if (!ctx.userId) {
      throw new TRPCError({ code: 'UNAUTHORIZED' });
    }

    return getUserSubscriptions(ctx.userId);
  }),

  /**
   * Cancels a subscription.
   *
   * @param input - Subscription ID
   * @returns Success status
   * @throws {TRPCError} NOT_FOUND if subscription doesn't exist or doesn't belong to user
   */
  cancel: protectedProcedure
    .input(z.object({ subscriptionId: z.string().uuid() }))
    .mutation(async ({ input, ctx }) => {
      if (!ctx.userId) {
        throw new TRPCError({ code: 'UNAUTHORIZED' });
      }

      // Verify subscription belongs to user
      const [subscription] = await db
        .select()
        .from(subscriptions)
        .where(
          and(
            eq(subscriptions.id, input.subscriptionId),
            eq(subscriptions.userId, ctx.userId)
          )
        )
        .limit(1);

      if (!subscription) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Subscription not found',
        });
      }

      // Cancel in Stripe
      await cancelSubscription(subscription.stripeSubscriptionId);

      // Update in database (webhook will also update, but do it here for immediate feedback)
      await db
        .update(subscriptions)
        .set({
          status: 'canceled',
          updatedAt: new Date(),
        })
        .where(eq(subscriptions.id, input.subscriptionId));

      return { success: true };
    }),
});
