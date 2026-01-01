import { seedUsers } from './users';
import { seedLeagues } from './leagues';
import { seedTeams } from './teams';
import { seedSubscriptions } from './subscriptions';
import { seedMatchStats } from './match-stats';
import { seedBettingRecommendations } from './betting-recommendations';

/**
 * Seeds the database with comprehensive test data.
 *
 * Creates:
 * - Test users (admin@example.com, user@example.com)
 * - Multiple leagues (Premier League, La Liga, Bundesliga, Serie A)
 * - Teams for each league
 * - Subscriptions for admin@example.com to all leagues
 * - Match stats for finished matches
 * - Betting recommendations for some matches
 *
 * Safe to run multiple times - checks for existing data first.
 */
export async function seed() {
  console.log('[seed]: 🌱 Seeding database...');

  // Seed in order of dependencies
  const userIds = await seedUsers();
  const adminUserId = userIds['admin@example.com'];
  if (!adminUserId) {
    throw new Error('Admin user not found after seeding');
  }

  const leagueIds = await seedLeagues();
  const teamIds = await seedTeams(leagueIds);

  await seedSubscriptions(adminUserId, leagueIds);
  await seedMatchStats();
  await seedBettingRecommendations();

  // Summary
  console.log('[seed]: \n✨ Seeding complete!');
  console.log('[seed]: \n📋 Summary:');
  console.log(`[seed]:    - Users: 2`);
  console.log(`[seed]:    - Leagues: ${leagueIds.length}`);
  console.log(`[seed]:    - Teams: ${Object.keys(teamIds).length}`);
  console.log(
    `[seed]:    - Subscriptions: ${leagueIds.length} (for admin@example.com)`
  );
  console.log(
    `[seed]: \n💡 Note: Matches will be fetched from RapidAPI when you navigate to /matches`
  );
  console.log(
    `[seed]: \n🔑 Login credentials:\n   - admin@example.com / admin123\n   - user@example.com / user123`
  );
}

/**
 * Runs seed and properly handles errors.
 */
async function runSeed() {
  try {
    await seed();
    process.exit(0);
  } catch (error: unknown) {
    console.error('[runSeed]: \n❌ Seed failed:', error);

    if (error && typeof error === 'object' && 'code' in error) {
      const errorCode = String(error.code);
      const errorMessage =
        'message' in error && typeof error.message === 'string'
          ? error.message
          : '';

      if (errorCode === 'ECONNREFUSED') {
        console.error('[runSeed]: \n❌ Database connection refused!');
        console.error(
          '[runSeed]: PostgreSQL is not running or not accessible.\n'
        );
        console.error('[runSeed]: To fix:');
        console.error('[runSeed]: 1. If using Docker: bun run docker:up');
        console.error('[runSeed]: 2. If using local PostgreSQL:');
        console.error('[runSeed]:    - Windows: Start PostgreSQL service');
        console.error('[runSeed]:    - macOS: brew services start postgresql');
        console.error(
          '[runSeed]:    - Linux: sudo systemctl start postgresql\n'
        );
      } else if (
        errorCode === '28P01' ||
        errorMessage.includes('password authentication failed')
      ) {
        console.error('[runSeed]: \n❌ Database authentication failed!');
        console.error('[runSeed]: Invalid username or password.\n');
        console.error('[runSeed]: To fix:');
        console.error('[runSeed]: 1. Check your DATABASE_URL in .env file');
        console.error(
          '[runSeed]:    Format: postgresql://username:password@host:port/database'
        );
        console.error(
          '[runSeed]:    Example: postgresql://postgres:postgres@localhost:5432/myoro_arbihawk\n'
        );
        console.error('[runSeed]: 2. If using Docker Compose, default is:');
        console.error(
          '[runSeed]:    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/myoro_arbihawk\n'
        );
      } else if (
        errorCode === '3D000' ||
        errorMessage.includes('does not exist')
      ) {
        console.error('[runSeed]: \n❌ Database does not exist!');
        console.error('[runSeed]: The database needs to be created.\n');
        console.error('[runSeed]: To fix:');
        console.error('[runSeed]: 1. Run: bun run docker:up');
        console.error(
          '[runSeed]: 2. Or manually: createdb -U postgres myoro_arbihawk\n'
        );
      } else if (
        errorMessage.includes('relation') &&
        errorMessage.includes('does not exist')
      ) {
        console.error('[runSeed]: \n❌ Database tables do not exist!');
        console.error('[runSeed]: Migrations need to be run.\n');
        console.error('[runSeed]: To fix:');
        console.error('[runSeed]: 1. Run: bun run db:migrate');
        console.error('[runSeed]: 2. Or run full setup: bun run setup\n');
      } else {
        console.error('[runSeed]: \n❌ Database error:', errorCode);
        console.error(
          '[runSeed]: Check your DATABASE_URL and PostgreSQL connection.\n'
        );
      }
    } else {
      console.error('[runSeed]: \n❌ Unknown error occurred');
      console.error(
        '[runSeed]: Check your DATABASE_URL and PostgreSQL connection.\n'
      );
    }

    process.exit(1);
  }
}

// Run seed if this file is executed directly
// This check works when running with: bun run src/db/seed/index.ts
const scriptPath = process.argv[1] || '';
const isMainModule =
  scriptPath.includes('seed/index.ts') ||
  scriptPath.includes('seed/index') ||
  scriptPath.endsWith('seed.ts');

if (isMainModule) {
  void runSeed();
}
