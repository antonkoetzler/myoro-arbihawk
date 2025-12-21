'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

/**
 * Betting recommendation component.
 *
 * Displays a betting recommendation with confidence score.
 */
export function BettingRecommendation({
  recommendation,
  confidencePercentage,
  betType,
}: {
  recommendation: string;
  confidencePercentage: number;
  betType: 'win' | 'draw' | 'over' | 'under';
}) {
  const getConfidenceColor = () => {
    if (confidencePercentage >= 70) {
      return 'bg-green-500';
    } else if (confidencePercentage >= 50) {
      return 'bg-yellow-500';
    } else {
      return 'bg-red-500';
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className='flex items-center justify-between'>
          <CardTitle>{recommendation}</CardTitle>
          <Badge variant='outline'>{betType}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className='space-y-2'>
          <div className='flex items-center justify-between'>
            <span className='text-sm text-muted-foreground'>Confidence</span>
            <span className='font-semibold'>{confidencePercentage}%</span>
          </div>
          <div className='w-full bg-gray-200 rounded-full h-2'>
            <div
              className={`h-2 rounded-full ${getConfidenceColor()}`}
              style={{ width: `${confidencePercentage}%` }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
