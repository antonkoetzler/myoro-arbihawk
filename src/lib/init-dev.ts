import { autoSeed } from './seed-dev';

/**
 * Initialize development environment.
 *
 * This runs once when the app starts in development mode.
 */
if (process.env.NODE_ENV !== 'production') {
  // Run seed asynchronously without blocking
  autoSeed().catch(() => {
    // Ignore errors - seeding is optional
  });
}
