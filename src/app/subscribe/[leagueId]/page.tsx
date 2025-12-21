'use client';

import { useParams, useRouter } from 'next/navigation';
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
import { useEffect } from 'react';

/**
 * Subscription checkout page.
 *
 * Creates Stripe checkout session and redirects user to payment.
 */
export default function SubscribePage() {
  const params = useParams();
  const router = useRouter();
  const { t } = useTranslations();
  const { token } = useAuthStore();
  const leagueId = params.leagueId as string;

  const { data: league, isLoading: leagueLoading } =
    trpc.leagues.getById.useQuery({ leagueId }, { enabled: !!leagueId });

  const createCheckout = trpc.stripe.createCheckout.useMutation({
    onSuccess: (data) => {
      if (data.url) {
        window.location.href = data.url;
      }
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

  if (leagueLoading) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <p>{t('auth.loading')}</p>
      </div>
    );
  }

  if (!league) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <Card>
          <CardContent className='pt-6'>
            <p>League not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className='flex items-center justify-center min-h-screen p-4'>
      <Card className='w-full max-w-md'>
        <CardHeader>
          <CardTitle>{t('leagues.subscribe')}</CardTitle>
          <CardDescription>
            {league.name} - {league.country}
          </CardDescription>
        </CardHeader>
        <CardContent className='space-y-4'>
          <p className='text-sm text-muted-foreground'>
            Subscribe to access match statistics, betting recommendations, and
            real-time updates for {league.name}.
          </p>
          <Button
            onClick={() => createCheckout.mutate({ leagueId: league.id })}
            disabled={createCheckout.isPending}
            className='w-full'
          >
            {createCheckout.isPending
              ? t('auth.loading')
              : t('leagues.subscribe')}
          </Button>
          {createCheckout.error && (
            <p className='text-sm text-red-600'>
              {createCheckout.error.message}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
