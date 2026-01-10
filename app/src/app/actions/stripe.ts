'use server';

import { getUserId } from '@/lib/auth-server';
import { db } from '@/db';
import { leagues, users } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { createCheckoutSession } from '@/lib/stripe';
import { env } from '@/lib/env';

/**
 * Server Action to create a Stripe checkout session.
 */
export async function createCheckoutAction(leagueId: string) {
  const userId = await getUserId();

  if (!userId) {
    throw new Error('Unauthorized');
  }

  const [league] = await db
    .select()
    .from(leagues)
    .where(eq(leagues.id, leagueId))
    .limit(1);

  if (!league) {
    throw new Error('League not found');
  }

  if (!league.isActive) {
    throw new Error('League is not available for subscription');
  }

  const [user] = await db
    .select()
    .from(users)
    .where(eq(users.id, userId))
    .limit(1);

  if (!user) {
    throw new Error('User not found');
  }

  const priceId = env.STRIPE_PRICE_ID;

  if (!priceId) {
    throw new Error('Stripe price not configured');
  }

  const session = await createCheckoutSession(
    userId,
    user.email,
    league.id,
    league.name,
    priceId
  );

  if (!session.url) {
    throw new Error('Failed to create checkout session');
  }

  return { url: session.url };
}
