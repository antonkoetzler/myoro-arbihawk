'use client';

import { useParams, useRouter } from 'next/navigation';
import { trpc } from '@/utils/trpc';
import { useTranslations } from '@/hooks/use-translations';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuthStore } from '@/stores/auth-store';
import { useEffect } from 'react';

/**
 * League standings page.
 *
 * Displays league table/standings.
 */
export default function StandingsPage() {
  const params = useParams();
  const router = useRouter();
  const { t } = useTranslations();
  const { token } = useAuthStore();
  const leagueId = params.leagueId as string;

  const { data: league } = trpc.leagues.getById.useQuery(
    { leagueId },
    { enabled: !!token && !!leagueId }
  );

  useEffect(() => {
    if (!token) {
      router.push('/');
    }
  }, [token, router]);

  if (!token) {
    return null;
  }

  // TODO: Fetch standings from API
  // For now, display placeholder

  return (
    <div className='container mx-auto py-8'>
      <h1 className='text-4xl font-bold mb-8'>
        {league?.name || 'Standings'} - {t('leagues.title')}
      </h1>

      <Card>
        <CardHeader>
          <CardTitle>League Table</CardTitle>
        </CardHeader>
        <CardContent>
          <p className='text-muted-foreground'>
            Standings data will be displayed here once API integration is
            complete.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
