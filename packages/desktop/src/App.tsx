import { AppProvider, CounterScreen } from '@repo/shared';

export function App() {
  return (
    <AppProvider defaultLocale="en" apiBaseUrl="http://localhost:3000">
      <CounterScreen syncWithBackend={false} />
    </AppProvider>
  );
}

