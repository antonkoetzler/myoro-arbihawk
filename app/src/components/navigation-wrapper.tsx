'use client';

import { usePathname } from 'next/navigation';
import { NavigationClient } from './navigation-client';

/**
 * Client wrapper for Navigation that hides on home/login page.
 */
export function NavigationWrapper({
  hasSubscriptions,
}: {
  hasSubscriptions: boolean;
}) {
  const pathname = usePathname();

  // Hide navigation on home/login page
  if (pathname === '/') {
    return null;
  }

  return <NavigationClient hasSubscriptions={hasSubscriptions} />;
}
