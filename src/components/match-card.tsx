'use client';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';
import Link from 'next/link';
import { routes } from '@/lib/routes';
import { matches, teams } from '@/db/schema';

type Match = typeof matches.$inferSelect;
type Team = typeof teams.$inferSelect;

/**
 * Match card component.
 *
 * Displays match information in a card format.
 */
export function MatchCard({
  match,
  homeTeam,
  awayTeam,
}: {
  match: Match;
  homeTeam: Team | null;
  awayTeam: Team | null;
}) {
  const { t } = useTranslation();

  const getStatusBadge = () => {
    switch (match.status) {
      case 'live':
        return <Badge variant='destructive'>{t('matchesLive')}</Badge>;
      case 'finished':
        return <Badge variant='secondary'>{t('matchesFinished')}</Badge>;
      case 'scheduled':
        return <Badge variant='outline'>{t('matchesUpcoming')}</Badge>;
      default:
        return null;
    }
  };

  return (
    <Link href={routes.match(match.id) as '/matches/${string}'}>
      <Card className='hover:shadow-lg transition-shadow cursor-pointer'>
        <CardHeader>
          <div className='flex items-center justify-between'>
            <CardTitle className='text-lg'>
              {homeTeam?.name || 'TBD'} {t('matchesVs')}{' '}
              {awayTeam?.name || 'TBD'}
            </CardTitle>
            {getStatusBadge()}
          </div>
          <CardDescription>
            {format(new Date(match.date), 'PPP p')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {match.status === 'finished' || match.status === 'live' ? (
            <div className='text-2xl font-bold text-center'>
              {match.homeScore ?? '-'} - {match.awayScore ?? '-'}
            </div>
          ) : (
            <div className='text-center text-muted-foreground'>
              {format(new Date(match.date), 'p')}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
