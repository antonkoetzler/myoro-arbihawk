'use client';

import { useTheme } from 'next-themes';
import { useTranslation } from 'react-i18next';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { useEffect, useState, useTransition } from 'react';
import { MoreVertical } from 'lucide-react';
import { logoutAction } from '@/app/actions/auth';

/**
 * User menu dropdown component.
 *
 * Contains theme toggle and logout functionality.
 */
export function UserMenu() {
  const { theme, setTheme } = useTheme();
  const { t } = useTranslation();
  const [mounted, setMounted] = useState(false);
  const [_isPending, startTransition] = useTransition();

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  const handleLogout = () => {
    startTransition(async () => {
      await logoutAction();
      // Redirect happens in the server action
    });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant='outline' size='icon'>
          <MoreVertical className='h-4 w-4' />
          <span className='sr-only'>User menu</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align='end'>
        <DropdownMenuLabel>{t('themeTitle')}</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => setTheme('light')}>
          {t('themeLight')}
          {theme === 'light' && ' ✓'}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('dark')}>
          {t('themeDark')}
          {theme === 'dark' && ' ✓'}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('system')}>
          {t('themeSystem')}
          {theme === 'system' && ' ✓'}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout}>
          {t('authLogout')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
