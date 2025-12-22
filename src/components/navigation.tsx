import { getUserId } from '@/lib/auth-server';
import { getUserSubscriptions } from '@/lib/subscription-check';
import { NavigationWrapper } from './navigation-wrapper';

/**
 * Navigation component (Server Component).
 *
 * Checks authentication server-side and renders client component.
 * Hidden on the home/login page.
 */
export async function Navigation() {
  const userId = await getUserId();

  if (!userId) {
    return null;
  }

  const subscriptions = await getUserSubscriptions(userId);
  const hasSubscriptions = subscriptions && subscriptions.length > 0;

  return <NavigationWrapper hasSubscriptions={hasSubscriptions} />;
}
