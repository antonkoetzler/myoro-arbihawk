'use client';

import { useState, useTransition } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { routes } from '@/lib/routes';
import { format } from 'date-fns';
import { cancelSubscriptionAction } from '@/app/actions/subscriptions';

type SubscriptionWithLeague = Awaited<
  ReturnType<typeof import('@/lib/subscription-check').getUserSubscriptions>
>[0];

/**
 * Client component for subscriptions page interactivity.
 */
export function SubscriptionsClient({
  initialSubscriptions,
}: {
  initialSubscriptions: SubscriptionWithLeague[];
}) {
  const { t } = useTranslation();
  const router = useRouter();
  const [subscriptions, setSubscriptions] = useState(initialSubscriptions);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const handleCancel = (subscriptionId: string) => {
    if (!confirm(t('subscriptionsCancelConfirm'))) {
      return;
    }

    setError(null);
    startTransition(async () => {
      try {
        await cancelSubscriptionAction(subscriptionId);
        // Remove the canceled subscription from state
        setSubscriptions((prev) =>
          prev.filter((sub) => sub.subscription.id !== subscriptionId)
        );
        router.refresh(); // Refresh to update server components
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to cancel subscription'
        );
      }
    });
  };

  return (
    <div className='container mx-auto py-8'>
      <h1 className='text-4xl font-bold mb-8'>
        {t('subscriptionsMySubscriptions')}
      </h1>

      {!subscriptions || subscriptions.length === 0 ? (
        <Card>
          <CardContent className='pt-6'>
            <p className='text-center text-muted-foreground'>
              {t('subscriptionsNoSubscriptions')}
            </p>
            <Button
              onClick={() => router.push(routes.leagues)}
              className='w-full mt-4'
            >
              {t('leaguesBrowse')}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {subscriptions.map(({ subscription, league }) => (
            <Card key={subscription.id}>
              <CardHeader>
                <CardTitle>{league.name}</CardTitle>
                <CardDescription>{league.country}</CardDescription>
              </CardHeader>
              <CardContent className='space-y-4'>
                <div className='text-sm'>
                  <p className='text-muted-foreground'>
                    {t('subscriptionsRenewsOn')}:{' '}
                    {format(new Date(subscription.currentPeriodEnd), 'PPP')}
                  </p>
                  <p className='font-medium'>{t('subscriptionsActive')}</p>
                </div>
                <Button
                  variant='destructive'
                  onClick={() => handleCancel(subscription.id)}
                  disabled={isPending}
                  className='w-full'
                >
                  {isPending ? t('authLoading') : t('subscriptionsCancel')}
                </Button>
                {error && <p className='text-sm text-red-600 mt-2'>{error}</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {error && (
        <div className='mt-4 p-4 bg-red-50 border border-red-200 rounded'>
          <p className='text-sm text-red-600'>{error}</p>
        </div>
      )}
    </div>
  );
}
