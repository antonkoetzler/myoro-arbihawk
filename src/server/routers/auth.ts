import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { createUser, findUserByEmail, verifyPassword } from '../../lib/auth';
import { createToken } from '../../lib/jwt';
import { publicProcedure, router } from '../trpc';
import { cookies } from 'next/headers';
import { env } from '@/lib/env';

/**
 * Zod schema for user signup input validation.
 */
const signupSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

/**
 * Zod schema for user login input validation.
 */
const loginSchema = z.object({
  email: z.string().email(),
  password: z.string(),
});

/**
 * Authentication router containing signup and login procedures.
 *
 * All procedures are public (no authentication required to call them).
 */
export const authRouter = router({
  /**
   * Creates a new user account.
   *
   * Validates email format and password length, checks for existing users,
   * hashes the password, creates the user in the database, and returns a JWT token.
   *
   * @param input - Object containing email and password
   * @returns Object with JWT token and user info (id, email)
   * @throws {TRPCError} CONFLICT if user already exists
   *
   * @example
   * ```typescript
   * const result = await trpc.auth.signup.mutate({
   *   email: 'user@example.com',
   *   password: 'securepassword123'
   * });
   * // result.token - JWT token to store
   * // result.user.id - User UUID
   * // result.user.email - User email
   * ```
   */
  signup: publicProcedure.input(signupSchema).mutation(async ({ input }) => {
    const existingUser = await findUserByEmail(input.email);
    if (existingUser) {
      throw new TRPCError({
        code: 'CONFLICT',
        message: 'User already exists',
      });
    }

    const user = await createUser(input.email, input.password);
    const token = createToken(user.id);

    // Set auth token in httpOnly cookie
    const cookieStore = await cookies();
    cookieStore.set('auth-token', token, {
      httpOnly: true,
      secure: env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });

    return {
      user: {
        id: user.id,
        email: user.email,
      },
    };
  }),

  /**
   * Authenticates an existing user.
   *
   * Validates credentials, verifies password hash, and returns a JWT token
   * if authentication succeeds.
   *
   * @param input - Object containing email and password
   * @returns Object with JWT token and user info (id, email)
   * @throws {TRPCError} UNAUTHORIZED if email doesn't exist or password is incorrect
   *
   * @example
   * ```typescript
   * const result = await trpc.auth.login.mutate({
   *   email: 'user@example.com',
   *   password: 'securepassword123'
   * });
   * // Store result.token in localStorage
   * ```
   */
  login: publicProcedure.input(loginSchema).mutation(async ({ input }) => {
    const user = await findUserByEmail(input.email);
    if (!user) {
      throw new TRPCError({
        code: 'UNAUTHORIZED',
        message: 'Invalid credentials',
      });
    }

    const isValid = await verifyPassword(input.password, user.passwordHash);
    if (!isValid) {
      throw new TRPCError({
        code: 'UNAUTHORIZED',
        message: 'Invalid credentials',
      });
    }

    const token = createToken(user.id);

    // Set auth token in httpOnly cookie
    const cookieStore = await cookies();
    cookieStore.set('auth-token', token, {
      httpOnly: true,
      secure: env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });

    return {
      user: {
        id: user.id,
        email: user.email,
      },
    };
  }),

  /**
   * Logs out the current user.
   *
   * Clears the auth token cookie.
   */
  logout: publicProcedure.mutation(async () => {
    const cookieStore = await cookies();
    cookieStore.delete('auth-token');
    return { success: true };
  }),
});
