import { Stack } from 'expo-router';
import { AppProvider } from '@repo/shared';

export default function RootLayout() {
  return (
    <AppProvider defaultLocale="en" apiBaseUrl="http://localhost:3000">
      <Stack
        screenOptions={{
          headerShown: false,
        }}
      />
    </AppProvider>
  );
}

