import type { Metadata } from 'next';
import { Providers } from '@/components/providers';
import { ThemeToggle } from '@/components/theme-toggle';
import './globals.css';

export const metadata: Metadata = {
  title: 'myoro-arbihawk',
  description: 'Next.js app with tRPC',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang='en' suppressHydrationWarning>
      <body>
        <Providers>
          <div className='absolute top-4 right-4'>
            <ThemeToggle />
          </div>
          {children}
        </Providers>
      </body>
    </html>
  );
}
