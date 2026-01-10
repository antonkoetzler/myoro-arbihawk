import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

/**
 * API route to clear auth token cookie.
 *
 * Called by client on logout.
 */
export async function POST() {
  try {
    const cookieStore = await cookies();
    cookieStore.delete('auth-token');

    return NextResponse.json({ success: true });
  } catch {
    return NextResponse.json(
      { error: 'Failed to clear token' },
      { status: 500 }
    );
  }
}
