'use client';

import { useState } from 'react';
import Image from 'next/image';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { trpc } from '@/utils/trpc';
import type { League } from '@/db/schema';
import { format } from 'date-fns';

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
  const { t } = useTranslation();
  const [selectedLeagueId, setSelectedLeagueId] = useState<string | null>(
    subscriptions[0]?.league.id || null
  );

  const selectedLeague = subscriptions.find(
    (sub) => sub.league.id === selectedLeagueId
  )?.league;

  return (
    <div className='container mx-auto py-8'>
      <h1 className='text-4xl font-bold mb-8'>{t('statsTitle')}</h1>

      <div className='mb-6'>
        <label className='text-sm font-medium mb-2 block'>
          {t('leaguesTitle')}
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
  const { t } = useTranslation();
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const { data: teams, isLoading } = trpc.stats.getTeams.useQuery({
    leagueId: league.id,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className='pt-6'>
          <p className='text-center text-muted-foreground'>
            {t('authLoading')}
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
            {t('statsNoTeams')}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className='grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4'>
        {teams.map((team) => (
          <Card
            key={team.id}
            className='hover:shadow-lg transition-shadow cursor-pointer'
            onClick={() => setSelectedTeamId(team.id)}
          >
            <CardContent className='pt-6'>
              <div className='flex flex-col items-center space-y-2'>
                {team.logoUrl ? (
                  <Image
                    src={team.logoUrl}
                    alt={team.name}
                    width={64}
                    height={64}
                    className='object-contain'
                    unoptimized
                  />
                ) : (
                  <div className='w-16 h-16 rounded-full bg-muted flex items-center justify-center text-2xl font-bold'>
                    {team.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <p className='text-sm font-medium text-center'>{team.name}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {selectedTeamId && (
        <TeamStatsModal
          teamId={selectedTeamId}
          leagueId={league.id}
          open={!!selectedTeamId}
          onOpenChange={(open) => {
            if (!open) setSelectedTeamId(null);
          }}
        />
      )}
    </>
  );
}

/**
 * Modal component to display comprehensive team statistics.
 */
function TeamStatsModal({
  teamId,
  leagueId,
  open,
  onOpenChange,
}: {
  teamId: string;
  leagueId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { t } = useTranslation();
  const { data: stats, isLoading } = trpc.stats.getTeamStats.useQuery(
    {
      teamId,
      leagueId,
    },
    {
      enabled: open,
    }
  );

  if (!stats) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className='max-w-4xl max-h-[90vh] overflow-y-auto'>
          <DialogHeader>
            <DialogTitle>
              {isLoading ? t('authLoading') : t('statsTitle')}
            </DialogTitle>
          </DialogHeader>
          {isLoading && (
            <div className='text-center py-8'>
              <p className='text-muted-foreground'>{t('authLoading')}</p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='max-w-4xl max-h-[90vh] overflow-y-auto'>
        <DialogHeader>
          <DialogTitle className='flex items-center gap-3'>
            {stats.team.logoUrl && (
              <Image
                src={stats.team.logoUrl}
                alt={stats.team.name}
                width={40}
                height={40}
                className='object-contain'
                unoptimized
              />
            )}
            {stats.team.name}
          </DialogTitle>
        </DialogHeader>

        <div className='space-y-6'>
          {/* Overview Section */}
          <Card>
            <CardHeader>
              <CardTitle>{t('statsOverview')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsMatches')}
                  </p>
                  <p className='text-2xl font-bold'>{stats.matches}</p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsWins')}
                  </p>
                  <p className='text-2xl font-bold text-green-600'>
                    {stats.wins}
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsDraws')}
                  </p>
                  <p className='text-2xl font-bold text-yellow-600'>
                    {stats.draws}
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsLosses')}
                  </p>
                  <p className='text-2xl font-bold text-red-600'>
                    {stats.losses}
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsTotalGoals')}
                  </p>
                  <p className='text-2xl font-bold'>{stats.totalGoals}</p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsGoalsConceded')}
                  </p>
                  <p className='text-2xl font-bold'>{stats.goalsConceded}</p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsGoalsPerMatch')}
                  </p>
                  <p className='text-2xl font-bold'>
                    {stats.goalsPerMatch.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsGoalsConcededPerMatch')}
                  </p>
                  <p className='text-2xl font-bold'>
                    {stats.goalsConcededPerMatch.toFixed(2)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Home/Away Split */}
          <div className='grid md:grid-cols-2 gap-4'>
            <Card>
              <CardHeader>
                <CardTitle>
                  {t('statsHomeStats')} ({t('statsHome')})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-2'>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsMatches')}:
                    </span>
                    <span className='font-semibold'>
                      {stats.homeStats.matches}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsGoalsScored')}:
                    </span>
                    <span className='font-semibold'>
                      {stats.homeStats.goalsScored}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsGoalsConceded')}:
                    </span>
                    <span className='font-semibold'>
                      {stats.homeStats.goalsConceded}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsWins')}:
                    </span>
                    <span className='font-semibold text-green-600'>
                      {stats.homeStats.wins}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsDraws')}:
                    </span>
                    <span className='font-semibold text-yellow-600'>
                      {stats.homeStats.draws}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsLosses')}:
                    </span>
                    <span className='font-semibold text-red-600'>
                      {stats.homeStats.losses}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>
                  {t('statsAwayStats')} ({t('statsAway')})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-2'>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsMatches')}:
                    </span>
                    <span className='font-semibold'>
                      {stats.awayStats.matches}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsGoalsScored')}:
                    </span>
                    <span className='font-semibold'>
                      {stats.awayStats.goalsScored}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsGoalsConceded')}:
                    </span>
                    <span className='font-semibold'>
                      {stats.awayStats.goalsConceded}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsWins')}:
                    </span>
                    <span className='font-semibold text-green-600'>
                      {stats.awayStats.wins}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsDraws')}:
                    </span>
                    <span className='font-semibold text-yellow-600'>
                      {stats.awayStats.draws}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-muted-foreground'>
                      {t('statsLosses')}:
                    </span>
                    <span className='font-semibold text-red-600'>
                      {stats.awayStats.losses}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Betting Metrics */}
          <Card>
            <CardHeader>
              <CardTitle>{t('statsBettingMetrics')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsBttsPercentage')}
                  </p>
                  <p className='text-2xl font-bold'>
                    {stats.bttsPercentage.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsOver25')}
                  </p>
                  <p className='text-2xl font-bold'>
                    {stats.over25Percentage.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsOver15')}
                  </p>
                  <p className='text-2xl font-bold'>
                    {stats.over15Percentage.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsUnder25')}
                  </p>
                  <p className='text-2xl font-bold'>
                    {stats.under25Percentage.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsCleanSheets')}
                  </p>
                  <p className='text-2xl font-bold'>{stats.cleanSheets}</p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsWinPercentage')}
                  </p>
                  <p className='text-2xl font-bold text-green-600'>
                    {stats.winPercentage.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsDrawPercentage')}
                  </p>
                  <p className='text-2xl font-bold text-yellow-600'>
                    {stats.drawPercentage.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className='text-sm text-muted-foreground'>
                    {t('statsLossPercentage')}
                  </p>
                  <p className='text-2xl font-bold text-red-600'>
                    {stats.lossPercentage.toFixed(1)}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Form */}
          {stats.recentForm.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t('statsRecentForm')}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-2'>
                  {stats.recentForm.map((match, index) => (
                    <div
                      key={index}
                      className='flex items-center justify-between p-2 border rounded'
                    >
                      <div className='flex items-center gap-3'>
                        <span
                          className={`px-2 py-1 rounded text-sm font-semibold ${
                            match.result === 'W'
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                              : match.result === 'D'
                                ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                          }`}
                        >
                          {match.result}
                        </span>
                        <span className='font-medium'>{match.opponent}</span>
                      </div>
                      <div className='flex items-center gap-3'>
                        <span className='text-sm font-mono'>{match.score}</span>
                        <span className='text-xs text-muted-foreground'>
                          {format(match.date, 'MMM d, yyyy')}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
