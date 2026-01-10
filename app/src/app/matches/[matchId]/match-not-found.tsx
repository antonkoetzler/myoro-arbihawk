'use client';

import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '@/components/ui/card';

/**
 * Client component for match not found error.
 */
export function MatchNotFound() {
  const { t } = useTranslation();

  return (
    <div className='flex items-center justify-center min-h-screen'>
      <Card className='w-full max-w-md'>
        <CardContent className='pt-6 text-center'>
          <p>{t('matchDetailMatchNotFound')}</p>
        </CardContent>
      </Card>
    </div>
  );
}
