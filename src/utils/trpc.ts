import { createTRPCReact } from '@trpc/react-query';
import { httpBatchLink } from '@trpc/client';
import superjson from 'superjson';
import type { AppRouter } from '@/server/routers/_app';

/**
 * React hooks for calling tRPC procedures.
 *
 * Provides type-safe hooks like `trpc.auth.signup.useMutation()` and
 * `trpc.hello.useQuery()` with full TypeScript autocomplete.
 *
 * @example
 * ```typescript
 * const signup = trpc.auth.signup.useMutation();
 * const { data } = trpc.hello.useQuery();
 * ```
 */
export const trpc = createTRPCReact<AppRouter>();

/**
 * Retrieves the JWT token from localStorage.
 *
 * Only works in browser environment (returns null during SSR).
 *
 * @returns JWT token string if found, null otherwise
 */
const getAuthToken = () => {
  return typeof window !== 'undefined' ? localStorage.getItem('token') : null;
};

/**
 * tRPC client instance for making API calls.
 *
 * Configured to:
 * - Send requests to `/api/trpc` endpoint
 * - Include JWT token in Authorization header if available
 * - Use superjson for serialization (handles Dates, etc.)
 * - Batch multiple requests together for efficiency
 *
 * @example
 * ```typescript
 * // Used by trpc.Provider in components/providers.tsx
 * <trpc.Provider client={trpcClient}>
 *   {children}
 * </trpc.Provider>
 * ```
 */
export const trpcClient = trpc.createClient({
  links: [
    httpBatchLink({
      url: '/api/trpc',
      transformer: superjson,
      headers: () => {
        const token = getAuthToken();
        return token ? { authorization: `Bearer ${token}` } : {};
      },
    }),
  ],
});
