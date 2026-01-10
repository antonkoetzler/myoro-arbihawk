'use server';

import { cookies } from 'next/headers';
import { createUser, findUserByEmail, verifyPassword } from '@/lib/auth';
import { createToken } from '@/lib/jwt';
import { redirect } from 'next/navigation';
import { getUserSubscriptions } from '@/lib/subscription-check';
import { routes } from '@/lib/routes';
import { env } from '@/lib/env';

/**
 * Server Action to sign up a new user.
 */
export async function signupAction(email: string, password: string) {
  const existingUser = await findUserByEmail(email);
  if (existingUser) {
    throw new Error('User already exists');
  }

  const user = await createUser(email, password);
  const token = createToken(user.id);

  // Set auth token in httpOnly cookie
  const cookieStore = cookies();
  cookieStore.set('auth-token', token, {
    httpOnly: true,
    secure: env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 7, // 7 days
    path: '/',
  });

  // Check subscriptions and redirect
  const subscriptions = await getUserSubscriptions(user.id);
  if (subscriptions && subscriptions.length > 0) {
    redirect(routes.subscriptions);
  } else {
    redirect(routes.leagues);
  }
}

/**
 * Server Action to log in a user.
 */
export async function loginAction(email: string, password: string) {
  const user = await findUserByEmail(email);
  if (!user) {
    throw new Error('Invalid credentials');
  }

  const isValid = await verifyPassword(password, user.passwordHash);
  if (!isValid) {
    throw new Error('Invalid credentials');
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

  // Check subscriptions and redirect
  const subscriptions = await getUserSubscriptions(user.id);
  if (subscriptions && subscriptions.length > 0) {
    redirect(routes.subscriptions);
  } else {
    redirect(routes.leagues);
  }
}

/**
 * Server Action to log out a user.
 */
export async function logoutAction() {
  const cookieStore = await cookies();
  cookieStore.delete('auth-token');
  redirect(routes.home);
}
