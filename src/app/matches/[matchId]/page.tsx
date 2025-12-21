'use client';

import { useParams, useRouter } from 'next/navigation';
import { trpc } from '@/utils/trpc';
import { useTranslations } from '@/hooks/use-translations';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/auth-store';
import { format } from 'date-fns';
import { useEffect } from 'react';

/**
 * Match detail page.
 *
 * Displays detailed match information including statistics and betting recommendations.
 */
export default function MatchDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t } = useTranslations();
  const { token } = useAuthStore();
  const matchId = params.matchId as string;

  const { data: matchData, isLoading } = trpc.matches.getById.useQuery(
    { matchId },
    { enabled: !!token && !!matchId }
  );

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

  if (!matchData) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <Card>
          <CardContent className='pt-6'>
            <p>Match not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { match, homeTeam, awayTeam, stats } = matchData;

  return (
    <div className='container mx-auto py-8'>
      <div className='mb-8'>
        <h1 className='text-4xl font-bold mb-4'>
          {homeTeam?.name || 'TBD'} {t('matches.vs')} {awayTeam?.name || 'TBD'}
        </h1>
        <div className='flex items-center gap-4'>
          <Badge
            variant={match.status === 'live' ? 'destructive' : 'secondary'}
          >
            {match.status === 'live'
              ? t('matches.live')
              : match.status === 'finished'
                ? t('matches.finished')
                : t('matches.upcoming')}
          </Badge>
          <span className='text-muted-foreground'>
            {format(new Date(match.date), 'PPP p')}
          </span>
        </div>
      </div>

      {match.status === 'finished' || match.status === 'live' ? (
        <div className='text-center mb-8'>
          <div className='text-6xl font-bold'>
            {match.homeScore ?? '-'} - {match.awayScore ?? '-'}
          </div>
        </div>
      ) : null}

      {stats && (
        <Card className='mb-6'>
          <CardHeader>
            <CardTitle>Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className='grid grid-cols-2 gap-4'>
              <div>
                <p className='text-sm text-muted-foreground'>Possession</p>
                <p className='text-lg font-semibold'>
                  {stats.homePossession}% - {stats.awayPossession}%
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>Shots</p>
                <p className='text-lg font-semibold'>
                  {stats.homeShots} - {stats.awayShots}
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>Shots on Target</p>
                <p className='text-lg font-semibold'>
                  {stats.homeShotsOnTarget} - {stats.awayShotsOnTarget}
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>Corners</p>
                <p className='text-lg font-semibold'>
                  {stats.homeCorners} - {stats.awayCorners}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* TODO: Add betting recommendations component */}
    </div>
  );
}
