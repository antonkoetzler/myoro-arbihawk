import { verifyToken } from '../lib/jwt';

/**
 * Creates the tRPC context for each request.
 *
 * Extracts and verifies the JWT token from the Authorization header,
 * then provides the authenticated user ID to all tRPC procedures.
 *
 * @param headers - HTTP request headers
 * @returns Context object containing userId (null if not authenticated)
 *
 * @example
 * ```typescript
 * const ctx = await createContext(request.headers);
 * // ctx.userId is either a string (authenticated) or null (not authenticated)
 * ```
 */
export const createContext = async (headers: Headers) => {
  const authHeader = headers.get('authorization');
  const token = authHeader?.replace('Bearer ', '');

  let userId: string | null = null;
  if (token) {
    const payload = verifyToken(token);
    userId = payload?.userId || null;
  }

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
