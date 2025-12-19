import { createTRPCReact } from '@trpc/react-query';
import { httpBatchLink } from '@trpc/client';
import type { AppRouter } from '@repo/backend/trpc';

// Create tRPC React client
export const trpc = createTRPCReact<AppRouter>();

// Create tRPC client configuration
export function createTRPCClient(baseUrl: string = 'http://localhost:3000') {
  return trpc.createClient({
    links: [
      httpBatchLink({
        url: `${baseUrl}/trpc`,
      }),
    ],
  });
}

// HTTP client for non-tRPC requests
export async function httpClient<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

