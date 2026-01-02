'use client';

import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import { trpc, trpcClient } from '@/utils/trpc';
import '@/lib/i18n';

/**
 * Root providers component.
 *
 * Wraps the app with:
 * - tRPC client for API calls
 * - React Query for data fetching
 * - Theme provider for light/dark mode
 * - i18n initialization
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const [trpcClientState] = useState(() => trpcClient);

  return (
    <ThemeProvider attribute='class' defaultTheme='system' enableSystem>
      <trpc.Provider client={trpcClientState} queryClient={queryClient}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </trpc.Provider>
    </ThemeProvider>
  );
}
