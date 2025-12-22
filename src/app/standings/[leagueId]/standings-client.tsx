'use client';

import { useTranslations } from '@/hooks/use-translations';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { League } from '@/db/schema';

type Standing = Awaited<
  ReturnType<typeof import('@/lib/data-server').getLeagueStandings>
>[0];

/**
 * Client component for standings page.
 */
export function StandingsClient({
  league,
  standings,
}: {
  league: League;
  standings: Standing[];
}) {
  const { t } = useTranslations();

  return (
    <div className='container mx-auto py-8'>
      <h1 className='text-4xl font-bold mb-8'>
        {league.name} - {t('leagues.title')}
      </h1>

      {!standings || standings.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>League Table</CardTitle>
          </CardHeader>
          <CardContent>
            <p className='text-muted-foreground'>
              Standings data not available yet. Data will be populated after
              matches are synced.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>League Table</CardTitle>
          </CardHeader>
          <CardContent>
            <div className='overflow-x-auto'>
              <table className='w-full'>
                <thead>
                  <tr className='border-b'>
                    <th className='text-left p-2'>Pos</th>
                    <th className='text-left p-2'>Team</th>
                    <th className='text-center p-2'>P</th>
                    <th className='text-center p-2'>W</th>
                    <th className='text-center p-2'>D</th>
                    <th className='text-center p-2'>L</th>
                    <th className='text-center p-2'>GD</th>
                    <th className='text-center p-2'>Pts</th>
                  </tr>
                </thead>
                <tbody>
                  {standings.map((standing, index) => (
                    <tr key={standing.team.id} className='border-b'>
                      <td className='p-2'>{index + 1}</td>
                      <td className='p-2'>{standing.team.name}</td>
                      <td className='text-center p-2'>{standing.played}</td>
                      <td className='text-center p-2'>{standing.wins}</td>
                      <td className='text-center p-2'>{standing.draws}</td>
                      <td className='text-center p-2'>{standing.losses}</td>
                      <td className='text-center p-2'>
                        {standing.goalDifference}
                      </td>
                      <td className='text-center p-2 font-bold'>
                        {standing.points}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
