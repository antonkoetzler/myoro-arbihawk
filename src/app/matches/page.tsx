'use client';

import { useState, useEffect } from 'react';
import { trpc } from '@/utils/trpc';
import { useTranslations } from '@/hooks/use-translations';
import { MatchCard } from '@/components/match-card';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/auth-store';
import { useRouter } from 'next/navigation';

/**
 * Matches listing page.
 *
 * Displays matches for subscribed leagues with filtering options.
 */
export default function MatchesPage() {
  const { t } = useTranslations();
  const router = useRouter();
  const { token } = useAuthStore();
  const [selectedLeagueId, setSelectedLeagueId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<
    'scheduled' | 'live' | 'finished' | undefined
  >();

  const { data: subscriptions } =
    trpc.subscriptions.getMySubscriptions.useQuery(undefined, {
      enabled: !!token,
    });

  const { data: matches, isLoading } = trpc.matches.getByLeague.useQuery(
    {
      leagueId: selectedLeagueId || subscriptions?.[0]?.league.id || '',
      status: statusFilter,
    },
    {
      enabled:
        !!token &&
        !!selectedLeagueId &&
        !!subscriptions &&
        subscriptions.length > 0,
    }
  );

  useEffect(() => {
    if (!token) {
      router.push('/');
    }
  }, [token, router]);

  useEffect(() => {
    if (subscriptions && subscriptions.length > 0 && !selectedLeagueId) {
      setSelectedLeagueId(subscriptions[0].league.id);
    }
  }, [subscriptions, selectedLeagueId]);

  if (!token) {
    return null;
  }

  if (!subscriptions || subscriptions.length === 0) {
    return (
      <div className='container mx-auto py-8'>
        <Card>
          <CardContent className='pt-6'>
            <p className='text-center text-muted-foreground mb-4'>
              {t('subscriptions.noSubscriptions')}
            </p>
            <Button onClick={() => router.push('/leagues')} className='w-full'>
              {t('leagues.browse')}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className='container mx-auto py-8'>
      <h1 className='text-4xl font-bold mb-8'>{t('matches.title')}</h1>

      <div className='mb-6 space-y-4'>
        <div>
          <label className='text-sm font-medium mb-2 block'>
            {t('leagues.title')}
          </label>
          <select
            value={selectedLeagueId || ''}
            onChange={(e) => setSelectedLeagueId(e.target.value)}
            className='w-full p-2 border rounded'
          >
            {subscriptions.map(({ league }) => (
              <option key={league.id} value={league.id}>
                {league.name}
              </option>
            ))}
          </select>
        </div>

        <div className='flex gap-2'>
          <Button
            variant={statusFilter === undefined ? 'default' : 'outline'}
            onClick={() => setStatusFilter(undefined)}
          >
            All
          </Button>
          <Button
            variant={statusFilter === 'scheduled' ? 'default' : 'outline'}
            onClick={() => setStatusFilter('scheduled')}
          >
            {t('matches.upcoming')}
          </Button>
          <Button
            variant={statusFilter === 'live' ? 'default' : 'outline'}
            onClick={() => setStatusFilter('live')}
          >
            {t('matches.live')}
          </Button>
          <Button
            variant={statusFilter === 'finished' ? 'default' : 'outline'}
            onClick={() => setStatusFilter('finished')}
          >
            {t('matches.finished')}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <p>{t('auth.loading')}</p>
      ) : !matches || matches.length === 0 ? (
        <Card>
          <CardContent className='pt-6'>
            <p className='text-center text-muted-foreground'>
              No matches found
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {matches.map((match) => (
            <MatchCard
              key={match.id}
              match={match}
              homeTeam={null} // TODO: Fetch teams
              awayTeam={null} // TODO: Fetch teams
            />
          ))}
        </div>
      )}
    </div>
  );
}
