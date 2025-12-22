import { seed } from '@/db/seed';

/**
 * Auto-seeds database in development mode.
 *
 * This is called automatically when the dev server starts.
 * Only runs if NODE_ENV is not production.
 * Uses a global flag to ensure it only runs once per process.
 */
export async function autoSeed() {
  if (process.env.NODE_ENV === 'production') {
    return;
  }

  // Double-check with global flag to prevent multiple runs
  const globalForSeed = globalThis as typeof globalThis & {
    __seedRun?: boolean;
  };
  if (globalForSeed.__seedRun) {
    return;
  }

  try {
    await seed();
  } catch (error) {
    // Don't crash the app if seeding fails
    // This is expected if DB isn't running or already seeded
    console.warn(
      '[autoSeed]: Auto-seed warning:',
      error instanceof Error ? error.message : 'Unknown error'
    );
  }
}
