import { cookies } from 'next/headers';
import { verifyToken } from './jwt';

/**
 * Gets the authenticated user ID from cookies.
 *
 * Reads the JWT token from httpOnly cookies and verifies it.
 * Returns null if no token or token is invalid.
 *
 * @returns User ID if authenticated, null otherwise
 *
 * @example
 * ```typescript
 * const userId = await getUserId();
 * if (userId) {
 *   // User is authenticated
 * }
 * ```
 */
export async function getUserId(): Promise<string | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get('auth-token')?.value;

  if (!token) {
    return null;
  }

  const payload = verifyToken(token);
  return payload?.userId || null;
}

/**
 * Checks if a user is authenticated.
 *
 * @returns True if user has valid auth token, false otherwise
 */
export async function isAuthenticated(): Promise<boolean> {
  const userId = await getUserId();
  return userId !== null;
}
