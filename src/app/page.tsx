'use client';

import { useState } from 'react';
import { trpc } from '@/utils/trpc';
import { useAuthStore } from '@/stores/auth-store';
import { useTranslations } from '@/hooks/use-translations';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * Home page component with authentication form.
 *
 * Handles login and signup with Zustand state management and shadcn UI components.
 */
export default function Home() {
  const { t } = useTranslations();
  const { token, setToken } = useAuthStore();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const signup = trpc.auth.signup.useMutation();
  const login = trpc.auth.login.useMutation();
  const { data: helloData } = trpc.hello.useQuery(undefined, {
    enabled: !!token,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = isLogin
        ? await login.mutateAsync({ email, password })
        : await signup.mutateAsync({ email, password });

      if (result.token) {
        setToken(result.token);
      }
    } catch (error) {
      console.error('Auth error:', error);
    }
  };

  if (token && helloData) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <h1 className='text-4xl font-bold'>{t('greeting.hello')}</h1>
      </div>
    );
  }

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
            <Button
              type='submit'
              disabled={signup.isPending || login.isPending}
              className='w-full'
            >
              {signup.isPending || login.isPending
                ? t('auth.loading')
                : isLogin
                  ? t('auth.login')
                  : t('auth.signup')}
            </Button>
          </form>
          <Button onClick={() => setIsLogin(!isLogin)} className='w-full mt-4'>
            {isLogin ? t('auth.noAccount') : t('auth.hasAccount')}
          </Button>
          {(signup.error || login.error) && (
            <div className='text-red-600 text-sm text-center mt-4'>
              {signup.error?.message || login.error?.message}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
