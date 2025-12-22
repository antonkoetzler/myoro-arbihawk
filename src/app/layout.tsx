import type { Metadata } from 'next';
import { Providers } from '@/components/providers';
import { Navigation } from '@/components/navigation';
import { ErrorBoundary } from '@/components/error-boundary';
import './globals.css';

export const metadata: Metadata = {
  title: 'Myoro Arbihawk',
  description:
    'Sports analysis application for soccer leagues with subscription-based access, real-time match statistics, and AI-powered betting recommendations.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang='en' suppressHydrationWarning>
      <body>
        <ErrorBoundary>
          <Providers>
            <Navigation />
            {children}
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
