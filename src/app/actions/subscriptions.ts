'use server';

import { getUserId } from '@/lib/auth-server';
import { db } from '@/db';
import { subscriptions } from '@/db/schema';
import { eq, and } from 'drizzle-orm';
import { cancelSubscription } from '@/lib/stripe';
import { revalidatePath } from 'next/cache';

/**
 * Server Action to cancel a subscription.
 */
export async function cancelSubscriptionAction(subscriptionId: string) {
  const userId = await getUserId();

  if (!userId) {
    throw new Error('Unauthorized');
  }

  // Verify subscription belongs to user
  const [subscription] = await db
    .select()
    .from(subscriptions)
    .where(
      and(
        eq(subscriptions.id, subscriptionId),
        eq(subscriptions.userId, userId)
      )
    )
    .limit(1);

  if (!subscription) {
    throw new Error('Subscription not found');
  }

  // Cancel in Stripe
  await cancelSubscription(subscription.stripeSubscriptionId);

  // Update in database
  await db
    .update(subscriptions)
    .set({
      status: 'canceled',
      updatedAt: new Date(),
    })
    .where(eq(subscriptions.id, subscriptionId));

  // Revalidate the subscriptions page
  revalidatePath('/subscriptions');

  return { success: true };
}
