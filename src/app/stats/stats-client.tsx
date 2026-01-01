'use client';

import { useState } from 'react';
import { useTranslations } from '@/hooks/use-translations';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { trpc } from '@/utils/trpc';
import type { League } from '@/db/schema';

type SubscriptionWithLeague = Awaited<
  ReturnType<typeof import('@/lib/subscription-check').getUserSubscriptions>
>[0];

/**
 * Client component for stats page.
 */
export function StatsClient({
  subscriptions,
}: {
  subscriptions: SubscriptionWithLeague[];
}) {
  const { t } = useTranslations();
  const [selectedLeagueId, setSelectedLeagueId] = useState<string | null>(
    subscriptions[0]?.league.id || null
  );

  const selectedLeague = subscriptions.find(
    (sub) => sub.league.id === selectedLeagueId
  )?.league;

  return (
    <div className='container mx-auto py-8'>
      <h1 className='text-4xl font-bold mb-8'>{t('stats.title')}</h1>

      <div className='mb-6'>
        <label className='text-sm font-medium mb-2 block'>
          {t('leagues.title')}
        </label>
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {subscriptions.map(({ league }) => (
            <Button
              key={league.id}
              variant={selectedLeagueId === league.id ? 'default' : 'outline'}
              onClick={() => setSelectedLeagueId(league.id)}
              className='h-auto py-4'
            >
              <div className='text-center'>
                <div className='font-semibold'>{league.name}</div>
                <div className='text-sm opacity-80'>{league.country}</div>
              </div>
            </Button>
          ))}
        </div>
      </div>

      {selectedLeague && <TeamStatsList league={selectedLeague} />}
    </div>
  );
}

/**
 * Component to display team stats for a league.
 */
function TeamStatsList({ league }: { league: League }) {
  const { t } = useTranslations();
  const { data: teams, isLoading } = trpc.stats.getTeams.useQuery({
    leagueId: league.id,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className='pt-6'>
          <p className='text-center text-muted-foreground'>
            {t('auth.loading')}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!teams || teams.length === 0) {
    return (
      <Card>
        <CardContent className='pt-6'>
          <p className='text-center text-muted-foreground'>
            {t('stats.noTeams')}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
      {teams.map((team: { id: string; name: string }) => (
        <TeamStatsCard key={team.id} teamId={team.id} leagueId={league.id} />
      ))}
    </div>
  );
}

/**
 * Component to display stats for a single team.
 */
function TeamStatsCard({
  teamId,
  leagueId,
}: {
  teamId: string;
  leagueId: string;
}) {
  const { t } = useTranslations();
  const { data: stats, isLoading } = trpc.stats.getTeamStats.useQuery({
    teamId,
    leagueId,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className='pt-6'>
          <p className='text-center text-muted-foreground'>
            {t('auth.loading')}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{stats.team.name}</CardTitle>
      </CardHeader>
      <CardContent className='space-y-2'>
        <div className='grid grid-cols-2 gap-2 text-sm'>
          <div>
            <span className='text-muted-foreground'>{t('stats.wins')}:</span>
            <span className='ml-2 font-semibold'>{stats.wins}</span>
          </div>
          <div>
            <span className='text-muted-foreground'>{t('stats.draws')}:</span>
            <span className='ml-2 font-semibold'>{stats.draws}</span>
          </div>
          <div>
            <span className='text-muted-foreground'>{t('stats.losses')}:</span>
            <span className='ml-2 font-semibold'>{stats.losses}</span>
          </div>
          <div>
            <span className='text-muted-foreground'>
              {t('stats.totalGoals')}:
            </span>
            <span className='ml-2 font-semibold'>{stats.totalGoals}</span>
          </div>
          <div>
            <span className='text-muted-foreground'>
              {t('stats.totalShots')}:
            </span>
            <span className='ml-2 font-semibold'>{stats.totalShots}</span>
          </div>
          <div>
            <span className='text-muted-foreground'>
              {t('stats.shotsOnTarget')}:
            </span>
            <span className='ml-2 font-semibold'>
              {stats.totalShotsOnTarget}
            </span>
          </div>
          <div>
            <span className='text-muted-foreground'>
              {t('stats.goalsPerMatch')}:
            </span>
            <span className='ml-2 font-semibold'>
              {stats.goalsPerMatch.toFixed(2)}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
