'use client';

import { useRouter } from 'next/navigation';
import { useTranslations } from '@/hooks/use-translations';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { routes } from '@/lib/routes';
import type { League } from '@/db/schema';

/**
 * Client component for leagues page interactivity.
 */
export function LeaguesClient({
  leagues,
  isAuthenticated,
}: {
  leagues: League[];
  isAuthenticated: boolean;
}) {
  const { t } = useTranslations();
  const router = useRouter();

  const handleSubscribe = (leagueId: string) => {
    if (!isAuthenticated) {
      router.push(routes.home);
      return;
    }
    router.push(routes.subscribe(leagueId));
  };

  return (
    <div className='container mx-auto py-8'>
      <h1 className='text-4xl font-bold mb-8'>{t('leagues.title')}</h1>

      {!leagues || leagues.length === 0 ? (
        <Card>
          <CardContent className='pt-6'>
            <p className='text-center text-muted-foreground'>
              {t('leagues.noLeagues')}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {leagues.map((league) => (
            <Card key={league.id}>
              <CardHeader>
                <CardTitle>{league.name}</CardTitle>
                <CardDescription>{league.country}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  onClick={() => handleSubscribe(league.id)}
                  className='w-full'
                  disabled={!isAuthenticated}
                >
                  {t('leagues.subscribe')}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
