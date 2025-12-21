import { seed } from '@/db/seed';

/**
 * Auto-seeds database in development mode.
 *
 * This is called automatically when the dev server starts.
 * Only runs if NODE_ENV is not production.
 */
export async function autoSeed() {
  if (process.env.NODE_ENV === 'production') {
    return;
  }

  try {
    await seed();
  } catch (error) {
    // Don't crash the app if seeding fails
    // This is expected if DB isn't running or already seeded
    console.warn(
      'Auto-seed warning:',
      error instanceof Error ? error.message : 'Unknown error'
    );
  }
}
