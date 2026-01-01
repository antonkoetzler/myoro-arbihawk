'use client';

import { useState, useTransition } from 'react';
import { useTranslations } from '@/hooks/use-translations';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { signupAction, loginAction } from '@/app/actions/auth';

/**
 * Home page component with authentication form.
 *
 * Client component for login/signup interactivity.
 * Uses Server Actions for authentication.
 */
export default function Home() {
  const { t } = useTranslations();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    startTransition(() => {
      void (async () => {
        try {
          if (isLogin) {
            await loginAction(email, password);
          } else {
            await signupAction(email, password);
          }
          // Redirect happens in the server action
        } catch (err) {
          setError(err instanceof Error ? err.message : 'An error occurred');
        }
      })();
    });
  };

  return (
    <div className='flex items-center justify-center min-h-screen p-4'>
      <Card className='w-full max-w-md'>
        <CardHeader>
          <CardTitle className='text-center'>
            {isLogin ? t('auth.login') : t('auth.signup')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className='space-y-4'>
            <div className='space-y-2'>
              <Label htmlFor='email'>{t('auth.email')}</Label>
              <Input
                id='email'
                type='email'
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className='space-y-2'>
              <Label htmlFor='password'>{t('auth.password')}</Label>
              <Input
                id='password'
                type='password'
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <Button type='submit' disabled={isPending} className='w-full'>
              {isPending
                ? t('auth.loading')
                : isLogin
                  ? t('auth.login')
                  : t('auth.signup')}
            </Button>
          </form>
          <Button onClick={() => setIsLogin(!isLogin)} className='w-full mt-4'>
            {isLogin ? t('auth.noAccount') : t('auth.hasAccount')}
          </Button>
          {error && (
            <div className='text-red-600 text-sm text-center mt-4'>{error}</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
