'use client';

import { trpc } from '@/utils/trpc';
import { useTranslations } from '@/hooks/use-translations';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/auth-store';
import { useRouter } from 'next/navigation';
import { format } from 'date-fns';
import { format } from 'date-fns';

/**
 * Subscriptions management page.
 *
 * Displays user's active subscriptions and allows cancellation.
 */
export default function SubscriptionsPage() {
  const { t } = useTranslations();
  const router = useRouter();
  const { token } = useAuthStore();
  const {
    data: subscriptions,
    isLoading,
    refetch,
  } = trpc.subscriptions.getMySubscriptions.useQuery(undefined, {
    enabled: !!token,
  });

  const cancelMutation = trpc.subscriptions.cancel.useMutation({
    onSuccess: () => {
      refetch();
    },
  });

  useEffect(() => {
    if (!token) {
      router.push('/');
    }
  }, [token, router]);

  if (!token) {
    return null;
  }

  if (isLoading) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <p>{t('auth.loading')}</p>
      </div>
    );
  }

  return (
    <div className='container mx-auto py-8'>
      <h1 className='text-4xl font-bold mb-8'>
        {t('subscriptions.mySubscriptions')}
      </h1>

      {!subscriptions || subscriptions.length === 0 ? (
        <Card>
          <CardContent className='pt-6'>
            <p className='text-center text-muted-foreground'>
              {t('subscriptions.noSubscriptions')}
            </p>
            <Button
              onClick={() => router.push('/leagues')}
              className='w-full mt-4'
            >
              {t('leagues.browse')}
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
                    {t('subscriptions.renewsOn')}:{' '}
                    {format(new Date(subscription.currentPeriodEnd), 'PPP')}
                  </p>
                  <p className='font-medium'>{t('subscriptions.active')}</p>
                </div>
                <Button
                  variant='destructive'
                  onClick={() => {
                    if (confirm(t('subscriptions.cancelConfirm'))) {
                      cancelMutation.mutate({
                        subscriptionId: subscription.id,
                      });
                    }
                  }}
                  disabled={cancelMutation.isPending}
                  className='w-full'
                >
                  {cancelMutation.isPending
                    ? t('auth.loading')
                    : t('subscriptions.cancel')}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
