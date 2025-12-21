'use client';

import { trpc } from '@/utils/trpc';
import { useTranslations } from '@/hooks/use-translations';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';

/**
 * Leagues browsing page.
 *
 * Displays all available leagues with subscription options.
 */
export default function LeaguesPage() {
  const { t } = useTranslations();
  const router = useRouter();
  const { token } = useAuthStore();
  const { data: leagues, isLoading } = trpc.leagues.getAll.useQuery({
    activeOnly: true,
  });

  const handleSubscribe = (leagueId: string) => {
    if (!token) {
      router.push('/');
      return;
    }
    router.push(`/subscribe/${leagueId}`);
  };

  if (isLoading) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <p>{t('auth.loading')}</p>
      </div>
    );
  }

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
                  disabled={!token}
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
