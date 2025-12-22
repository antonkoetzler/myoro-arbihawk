import { redirect } from 'next/navigation';
import { getUserId } from '@/lib/auth-server';
import { getUserSubscriptions } from '@/lib/subscription-check';
import { StatsClient } from './stats-client';

/**
 * Stats page (Server Component).
 *
 * Displays league selection for viewing team statistics.
 */
export default async function StatsPage() {
  const userId = await getUserId();

  if (!userId) {
    redirect('/');
  }

  const subscriptions = await getUserSubscriptions(userId);

  if (!subscriptions || subscriptions.length === 0) {
    redirect('/leagues');
  }

  return <StatsClient subscriptions={subscriptions} />;
}
