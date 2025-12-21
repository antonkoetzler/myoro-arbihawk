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
import { useTranslations } from '@/hooks/use-translations';
import Link from 'next/link';

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
  match: {
    id: string;
    date: Date;
    status: 'scheduled' | 'live' | 'finished' | 'postponed' | 'canceled';
    homeScore: number | null;
    awayScore: number | null;
  };
  homeTeam: { name: string; logoUrl: string | null } | null;
  awayTeam: { name: string; logoUrl: string | null } | null;
}) {
  const { t } = useTranslations();

  const getStatusBadge = () => {
    switch (match.status) {
      case 'live':
        return <Badge variant='destructive'>{t('matches.live')}</Badge>;
      case 'finished':
        return <Badge variant='secondary'>{t('matches.finished')}</Badge>;
      case 'scheduled':
        return <Badge variant='outline'>{t('matches.upcoming')}</Badge>;
      default:
        return null;
    }
  };

  return (
    <Link href={`/matches/${match.id}`}>
      <Card className='hover:shadow-lg transition-shadow cursor-pointer'>
        <CardHeader>
          <div className='flex items-center justify-between'>
            <CardTitle className='text-lg'>
              {homeTeam?.name || 'TBD'} {t('matches.vs')}{' '}
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
