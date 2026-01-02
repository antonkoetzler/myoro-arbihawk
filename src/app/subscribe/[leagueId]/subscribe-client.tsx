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
import type { League } from '@/db/schema';
import { createCheckoutAction } from '@/app/actions/stripe';

/**
 * Client component for subscription checkout interactivity.
 */
export function SubscribeClient({ league }: { league: League }) {
  const { t } = useTranslation();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const handleSubscribe = () => {
    setError(null);
    startTransition(async () => {
      try {
        const { url } = await createCheckoutAction(league.id);
        if (url) {
          window.location.href = url;
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to create checkout'
        );
      }
    });
  };

  return (
    <div className='flex items-center justify-center min-h-screen p-4'>
      <Card className='w-full max-w-md'>
        <CardHeader>
          <CardTitle>{t('leaguesSubscribe')}</CardTitle>
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
            onClick={handleSubscribe}
            disabled={isPending}
            className='w-full'
          >
            {isPending ? t('authLoading') : t('leaguesSubscribe')}
          </Button>
          {error && <p className='text-sm text-red-600'>{error}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
