import { db } from '@/db';
import { subscriptions, leagues } from '@/db/schema';
import { eq, and } from 'drizzle-orm';

/**
 * Checks if a user has an active subscription to a league.
 *
 * @param userId - User ID
 * @param leagueId - League ID
 * @returns True if user has active subscription, false otherwise
 */
export async function hasActiveSubscription(
  userId: string,
  leagueId: string
): Promise<boolean> {
  const [subscription] = await db
    .select()
    .from(subscriptions)
    .where(
      and(
        eq(subscriptions.userId, userId),
        eq(subscriptions.leagueId, leagueId),
        eq(subscriptions.status, 'active')
      )
    )
    .limit(1);

  return !!subscription;
}

/**
 * Gets all active subscriptions for a user.
 *
 * @param userId - User ID
 * @returns Array of subscription objects with league information
 */
export async function getUserSubscriptions(userId: string) {
  return db
    .select({
      subscription: subscriptions,
      league: leagues,
    })
    .from(subscriptions)
    .innerJoin(leagues, eq(subscriptions.leagueId, leagues.id))
    .where(
      and(eq(subscriptions.userId, userId), eq(subscriptions.status, 'active'))
    );
}
