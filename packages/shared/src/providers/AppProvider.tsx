import { type ReactNode, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TamaguiProvider, config } from '@repo/ui';
import { I18nProvider, type SupportedLocale } from '@repo/i18n';
import { trpc, createTRPCClient } from '../services/api';

interface AppProviderProps {
  children: ReactNode;
  /** Default locale for the app */
  defaultLocale?: SupportedLocale;
  /** Backend API base URL */
  apiBaseUrl?: string;
}

export function AppProvider({
  children,
  defaultLocale = 'en',
  apiBaseUrl = 'http://localhost:3000',
}: AppProviderProps) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60, // 1 minute
        refetchOnWindowFocus: false,
      },
    },
  }));
  
  const [trpcClient] = useState(() => createTRPCClient(apiBaseUrl));

  return (
    <trpc.Provider client={trpcClient} queryClient={queryClient}>
      <QueryClientProvider client={queryClient}>
        <TamaguiProvider config={config}>
          <I18nProvider defaultLocale={defaultLocale}>
            {children}
          </I18nProvider>
        </TamaguiProvider>
      </QueryClientProvider>
    </trpc.Provider>
  );
}

