import { redirect } from 'next/navigation';
import { getUserId } from '@/lib/auth-server';
import { getUserSubscriptions } from '@/lib/subscription-check';
import { SubscriptionsClient } from './subscriptions-client';

/**
 * Subscriptions management page (Server Component).
 *
 * Fetches user subscriptions on the server.
 */
export default async function SubscriptionsPage() {
  const userId = await getUserId();

  if (!userId) {
    redirect('/');
  }

  const subscriptions = await getUserSubscriptions(userId);

  return <SubscriptionsClient initialSubscriptions={subscriptions} />;
}
