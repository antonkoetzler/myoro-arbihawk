'use client';

import { useRouter, usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { useTranslation } from 'react-i18next';
import { UserMenu } from '@/components/user-menu';
import { routes } from '@/lib/routes';

/**
 * Client component for navigation interactivity.
 */
export function NavigationClient({
  hasSubscriptions,
}: {
  hasSubscriptions: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { t } = useTranslation();

  const isActive = (path: string) => pathname === path;

  return (
    <nav className='border-b bg-background'>
      <div className='container mx-auto px-4'>
        <div className='flex items-center justify-between h-16'>
          <div className='flex items-center gap-4'>
            <Button
              variant={isActive(routes.subscriptions) ? 'default' : 'ghost'}
              onClick={() => router.push(routes.subscriptions)}
            >
              {t('subscriptionsMySubscriptions')}
            </Button>
            <Button
              variant={isActive(routes.leagues) ? 'default' : 'ghost'}
              onClick={() => router.push(routes.leagues)}
            >
              {t('leaguesTitle')}
            </Button>
            <Button
              variant={isActive(routes.matches) ? 'default' : 'ghost'}
              onClick={() => router.push(routes.matches)}
            >
              {t('matchesTitle')}
            </Button>
            {hasSubscriptions && (
              <Button
                variant={isActive(routes.stats) ? 'default' : 'ghost'}
                onClick={() => router.push(routes.stats)}
              >
                {t('statsTitle')}
              </Button>
            )}
          </div>
          <UserMenu />
        </div>
      </div>
    </nav>
  );
}
