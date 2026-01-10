'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { MatchCard } from '@/components/match-card';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { routes } from '@/lib/routes';
import type { Match } from '@/db/schema';
import { trpc } from '@/utils/trpc';

type SubscriptionWithLeague = Awaited<
  ReturnType<typeof import('@/lib/subscription-check').getUserSubscriptions>
>[0];

/**
 * Client component for matches page interactivity.
 */
export function MatchesClient({
  subscriptions,
  matches: initialMatches,
  selectedLeagueId,
  statusFilter,
}: {
  subscriptions: SubscriptionWithLeague[];
  matches: Match[];
  selectedLeagueId: string | null;
  statusFilter: 'scheduled' | 'live' | undefined;
}) {
  const { t } = useTranslation();
  const router = useRouter();
  const [selectedLeague, setSelectedLeague] = useState(selectedLeagueId);
  const [status, setStatus] = useState<
    'scheduled' | 'live' | 'finished' | undefined
  >(statusFilter);

  // Teams will be fetched via tRPC when needed by MatchCard
  const handleLeagueChange = (leagueId: string) => {
    setSelectedLeague(leagueId);
    const params = new URLSearchParams();
    params.set('leagueId', leagueId);
    if (status) params.set('status', status);
    router.push(`${routes.matches}?${params.toString()}`);
  };

  const handleStatusChange = (
    newStatus: 'scheduled' | 'live' | 'finished' | undefined
  ) => {
    setStatus(newStatus);
    const params = new URLSearchParams();
    if (selectedLeague) params.set('leagueId', selectedLeague);
    if (newStatus) params.set('status', newStatus);
    router.push(`${routes.matches}?${params.toString()}`);
  };

  if (!subscriptions || subscriptions.length === 0) {
    return (
      <Card>
        <CardContent className='pt-6'>
          <p className='text-center text-muted-foreground mb-4'>
            {t('subscriptionsNoSubscriptions')}
          </p>
          <Button
            onClick={() => router.push(routes.leagues)}
            className='w-full'
          >
            {t('leaguesBrowse')}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className='container mx-auto py-8'>
      <h1 className='text-4xl font-bold mb-8'>{t('matchesTitle')}</h1>

      <div className='mb-6 space-y-4'>
        <div>
          <label className='text-sm font-medium mb-2 block'>
            {t('leaguesTitle')}
          </label>
          <select
            value={selectedLeague || ''}
            onChange={(e) => handleLeagueChange(e.target.value)}
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
            variant={status === undefined ? 'default' : 'outline'}
            onClick={() => handleStatusChange(undefined)}
          >
            {t('matchesAll')}
          </Button>
          <Button
            variant={status === 'scheduled' ? 'default' : 'outline'}
            onClick={() => handleStatusChange('scheduled')}
          >
            {t('matchesUpcoming')}
          </Button>
          <Button
            variant={status === 'live' ? 'default' : 'outline'}
            onClick={() => handleStatusChange('live')}
          >
            {t('matchesLive')}
          </Button>
        </div>
      </div>

      {!initialMatches || initialMatches.length === 0 ? (
        <Card>
          <CardContent className='pt-6'>
            <p className='text-center text-muted-foreground'>
              {t('matchesNoMatchesFound')}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {initialMatches.map((match) => (
            <MatchCardWithTeams key={match.id} match={match} />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Match card with teams fetched via tRPC.
 */
function MatchCardWithTeams({ match }: { match: Match }) {
  const { data: matchData } = trpc.matches.getById.useQuery(
    { matchId: match.id },
    { enabled: !!match.id }
  );

  return (
    <MatchCard
      match={match}
      homeTeam={matchData?.homeTeam || null}
      awayTeam={matchData?.awayTeam || null}
    />
  );
}
