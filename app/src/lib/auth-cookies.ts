'use client';

/**
 * Client-side utilities for auth cookie management.
 *
 * These functions are used by client components to interact with auth cookies.
 * The actual token is stored in httpOnly cookies (server-side only).
 */

/**
 * Sets the auth token cookie via API route.
 *
 * @param token - JWT token to store
 */
export async function setAuthToken(token: string): Promise<void> {
  await fetch('/api/auth/set-token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
}

/**
 * Clears the auth token cookie via API route.
 */
export async function clearAuthToken(): Promise<void> {
  await fetch('/api/auth/clear-token', {
    method: 'POST',
  });
}
