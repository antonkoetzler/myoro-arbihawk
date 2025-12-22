import { getUserId } from '../lib/auth-server';

/**
 * Creates the tRPC context for each request.
 *
 * Extracts and verifies the JWT token from cookies,
 * then provides the authenticated user ID to all tRPC procedures.
 *
 * @param headers - HTTP request headers (unused, kept for compatibility)
 * @returns Context object containing userId (null if not authenticated)
 *
 * @example
 * ```typescript
 * const ctx = await createContext(request.headers);
 * // ctx.userId is either a string (authenticated) or null (not authenticated)
 * ```
 */
export const createContext = async (_headers: Headers) => {
  const userId = await getUserId();

  return {
    userId,
  };
};

/**
 * Type definition for tRPC context.
 *
 * Used by tRPC procedures to access request-scoped data like the authenticated user ID.
 */
export type Context = Awaited<ReturnType<typeof createContext>>;
