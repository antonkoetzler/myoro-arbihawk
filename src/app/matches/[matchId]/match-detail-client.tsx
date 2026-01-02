'use client';

import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { BettingRecommendation } from '@/components/betting-recommendation';
import { trpc } from '@/utils/trpc';

type MatchData = Awaited<
  ReturnType<typeof import('@/lib/data-server').getMatchById>
>;

/**
 * Client component for match detail page interactivity.
 */
export function MatchDetailClient({
  matchData,
}: {
  matchData: NonNullable<MatchData>;
}) {
  const { t } = useTranslation();
  const { match, homeTeam, awayTeam, stats } = matchData;

  const { data: recommendations, isLoading: isLoadingRecommendations } =
    trpc.betting.getRecommendations.useQuery(
      { matchId: match.id },
      { enabled: !!match.id }
    );

  return (
    <div className='container mx-auto py-8'>
      <div className='mb-8'>
        <h1 className='text-4xl font-bold mb-4'>
          {homeTeam?.name || t('matchesTbd')} {t('matchesVs')}{' '}
          {awayTeam?.name || t('matchesTbd')}
        </h1>
        <div className='flex items-center gap-4'>
          <Badge
            variant={match.status === 'live' ? 'destructive' : 'secondary'}
          >
            {match.status === 'live'
              ? t('matchesLive')
              : match.status === 'finished'
                ? t('matchesFinished')
                : t('matchesUpcoming')}
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
            <CardTitle>{t('matchDetailStatistics')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className='grid grid-cols-2 gap-4'>
              <div>
                <p className='text-sm text-muted-foreground'>
                  {t('matchDetailPossession')}
                </p>
                <p className='text-lg font-semibold'>
                  {stats.homePossession}% - {stats.awayPossession}%
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>
                  {t('matchDetailShots')}
                </p>
                <p className='text-lg font-semibold'>
                  {stats.homeShots} - {stats.awayShots}
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>
                  {t('matchDetailShotsOnTarget')}
                </p>
                <p className='text-lg font-semibold'>
                  {stats.homeShotsOnTarget} - {stats.awayShotsOnTarget}
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>
                  {t('matchDetailCorners')}
                </p>
                <p className='text-lg font-semibold'>
                  {stats.homeCorners} - {stats.awayCorners}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card className='mb-6'>
        <CardHeader>
          <CardTitle>{t('matchDetailBettingRecommendations')}</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoadingRecommendations ? (
            <p className='text-muted-foreground'>
              {t('matchDetailLoadingRecommendations')}
            </p>
          ) : !recommendations || recommendations.length === 0 ? (
            <p className='text-muted-foreground'>
              {t('matchDetailNoRecommendations')}
            </p>
          ) : (
            <div className='space-y-4'>
              {recommendations.map((rec) => (
                <BettingRecommendation
                  key={rec.id}
                  recommendation={rec.recommendation}
                  confidencePercentage={rec.confidencePercentage}
                  betType={rec.betType}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
