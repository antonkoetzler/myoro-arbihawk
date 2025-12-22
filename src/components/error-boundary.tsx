'use client';

import { Component, type ReactNode } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useTranslations } from '@/hooks/use-translations';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary component to catch React errors.
 *
 * Displays a user-friendly error message instead of a white screen.
 * Users can retry or navigate away.
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(
      '[ErrorBoundary.componentDidCatch]: Error caught by boundary:',
      error,
      errorInfo
    );
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return <ErrorFallback error={this.state.error} />;
    }

    return this.props.children;
  }
}

/**
 * Default error fallback UI.
 */
function ErrorFallback({ error }: { error: Error | null }) {
  const { t } = useTranslations();

  return (
    <div className='flex items-center justify-center min-h-screen p-4'>
      <Card className='w-full max-w-md'>
        <CardHeader>
          <CardTitle>{t('common.somethingWentWrong')}</CardTitle>
        </CardHeader>
        <CardContent className='space-y-4'>
          <p className='text-sm text-muted-foreground'>
            {error?.message || t('common.unexpectedError')}
          </p>
          <div className='flex gap-2'>
            <Button
              onClick={() => window.location.reload()}
              variant='default'
              className='flex-1'
            >
              {t('common.reloadPage')}
            </Button>
            <Button
              onClick={() => (window.location.href = '/')}
              variant='outline'
              className='flex-1'
            >
              {t('common.goHome')}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
