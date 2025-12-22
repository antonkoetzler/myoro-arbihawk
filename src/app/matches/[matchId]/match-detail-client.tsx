'use client';

import { useTranslations } from '@/hooks/use-translations';
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
  const { t } = useTranslations();
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
          {homeTeam?.name || t('matches.tbd')} {t('matches.vs')}{' '}
          {awayTeam?.name || t('matches.tbd')}
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
            <CardTitle>{t('matchDetail.statistics')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className='grid grid-cols-2 gap-4'>
              <div>
                <p className='text-sm text-muted-foreground'>
                  {t('matchDetail.possession')}
                </p>
                <p className='text-lg font-semibold'>
                  {stats.homePossession}% - {stats.awayPossession}%
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>
                  {t('matchDetail.shots')}
                </p>
                <p className='text-lg font-semibold'>
                  {stats.homeShots} - {stats.awayShots}
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>
                  {t('matchDetail.shotsOnTarget')}
                </p>
                <p className='text-lg font-semibold'>
                  {stats.homeShotsOnTarget} - {stats.awayShotsOnTarget}
                </p>
              </div>
              <div>
                <p className='text-sm text-muted-foreground'>
                  {t('matchDetail.corners')}
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
          <CardTitle>{t('matchDetail.bettingRecommendations')}</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoadingRecommendations ? (
            <p className='text-muted-foreground'>
              {t('matchDetail.loadingRecommendations')}
            </p>
          ) : !recommendations || recommendations.length === 0 ? (
            <p className='text-muted-foreground'>
              {t('matchDetail.noRecommendations')}
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
