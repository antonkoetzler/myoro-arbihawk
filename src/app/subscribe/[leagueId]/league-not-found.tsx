'use client';

import { useTranslations } from '@/hooks/use-translations';
import { Card, CardContent } from '@/components/ui/card';

/**
 * Client component for league not found error.
 */
export function LeagueNotFound() {
  const { t } = useTranslations();

  return (
    <div className='flex items-center justify-center min-h-screen'>
      <Card className='w-full max-w-md'>
        <CardContent className='pt-6 text-center'>
          <p>{t('common.leagueNotFound')}</p>
        </CardContent>
      </Card>
    </div>
  );
}
