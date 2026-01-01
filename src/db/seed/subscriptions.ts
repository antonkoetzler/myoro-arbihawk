import { and, eq } from 'drizzle-orm';
import { db } from '../index';
import { subscriptions } from '../schema';

/**
 * Seeds subscriptions table with test data.
 *
 * @param userId - User ID to create subscriptions for
 * @param leagueIds - Array of league IDs to subscribe to
 */
export async function seedSubscriptions(
  userId: string,
  leagueIds: string[]
): Promise<void> {
  console.log('[seed]: \n💳 Creating subscriptions...');

  for (const leagueId of leagueIds) {
    const existing = await db
      .select()
      .from(subscriptions)
      .where(
        and(
          eq(subscriptions.userId, userId),
          eq(subscriptions.leagueId, leagueId)
        )
      )
      .limit(1);

    if (existing.length > 0) {
      console.log(`[seed]: ⏭️  Subscription already exists for league`);
      continue;
    }

    const periodEnd = new Date();
    periodEnd.setMonth(periodEnd.getMonth() + 1);

    await db.insert(subscriptions).values({
      userId,
      leagueId,
      stripeSubscriptionId: `sub_test_${leagueId.slice(0, 8)}`,
      stripeCustomerId: `cus_test_${userId.slice(0, 8)}`,
      status: 'active',
      currentPeriodEnd: periodEnd,
    });
    console.log(`[seed]: ✅ Created subscription for admin user`);
  }
}
