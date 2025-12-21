import jwt from 'jsonwebtoken';

/**
 * Secret key for signing JWT tokens.
 * Falls back to insecure default if not set in environment.
 *
 * @remarks Always set JWT_SECRET in production!
 */
const JWT_SECRET = process.env.JWT_SECRET || 'change-me-in-production';

/**
 * Token expiration time.
 * Tokens expire after 7 days.
 */
const JWT_EXPIRES_IN = '7d';

/**
 * Creates a JWT token for a user.
 *
 * Signs a token containing the user ID that expires after 7 days.
 * The token can be sent to the client and used for authenticated requests.
 *
 * @param userId - The user's UUID from the database
 * @returns Signed JWT token string
 *
 * @example
 * ```typescript
 * const token = createToken(user.id);
 * // Send token to client, store in localStorage
 * ```
 */
export const createToken = (userId: string): string => {
  return jwt.sign({ userId }, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
};

/**
 * Verifies and decodes a JWT token.
 *
 * Checks if the token is valid (not expired, correct signature) and
 * extracts the user ID from the payload.
 *
 * @param token - JWT token string from Authorization header
 * @returns Object with userId if valid, null if invalid/expired
 *
 * @example
 * ```typescript
 * const payload = verifyToken(tokenFromHeader);
 * if (payload) {
 *   const userId = payload.userId; // User is authenticated
 * } else {
 *   // Token invalid or expired
 * }
 * ```
 */
export const verifyToken = (token: string): { userId: string } | null => {
  try {
    const payload = jwt.verify(token, JWT_SECRET) as { userId: string };
    return payload;
  } catch {
    return null;
  }
};
