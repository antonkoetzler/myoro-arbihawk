import { eq } from 'drizzle-orm';
import { db } from './index';
import { users } from './schema';
import { hashPassword } from '../lib/auth';

/**
 * Seeds the database with initial test users.
 *
 * Creates two test users for development:
 * - admin@example.com / admin123
 * - user@example.com / user123
 *
 * Safe to run multiple times - checks for existing users first.
 *
 * @example
 * ```typescript
 * await seed();
 * ```
 */
export async function seed() {
  console.log('🌱 Seeding database...');

  const testUsers = [
    { email: 'admin@example.com', password: 'admin123' },
    { email: 'user@example.com', password: 'user123' },
  ];

  for (const { email, password } of testUsers) {
    // Check if user already exists
    const existing = await db
      .select()
      .from(users)
      .where(eq(users.email, email))
      .limit(1);

    if (existing.length > 0) {
      console.log(`⏭️  User ${email} already exists, skipping...`);
      continue;
    }

    // Create new user
    const passwordHash = await hashPassword(password);
    await db.insert(users).values({ email, passwordHash });
    console.log(`✅ Created user: ${email} / ${password}`);
  }

  console.log('✨ Seeding complete!');
}

/**
 * Runs seed and properly handles errors.
 */
async function runSeed() {
  try {
    await seed();
    process.exit(0);
  } catch (error: unknown) {
    console.error('\n❌ Seed failed:', error);

    if (error && typeof error === 'object' && 'code' in error) {
      const errorCode = error.code as string;
      const errorMessage =
        'message' in error && typeof error.message === 'string'
          ? error.message
          : '';

      if (errorCode === 'ECONNREFUSED') {
        console.error('\n❌ Database connection refused!');
        console.error('PostgreSQL is not running or not accessible.\n');
        console.error('To fix:');
        console.error('1. If using Docker: docker-compose up -d');
        console.error('2. If using local PostgreSQL:');
        console.error('   - Windows: Start PostgreSQL service');
        console.error('   - macOS: brew services start postgresql');
        console.error('   - Linux: sudo systemctl start postgresql\n');
      } else if (
        errorCode === '28P01' ||
        errorMessage.includes('password authentication failed')
      ) {
        console.error('\n❌ Database authentication failed!');
        console.error('Invalid username or password.\n');
        console.error('To fix:');
        console.error('1. Check your DATABASE_URL in .env file');
        console.error(
          '   Format: postgresql://username:password@host:port/database'
        );
        console.error(
          '   Example: postgresql://postgres:postgres@localhost:5432/myoro_arbihawk\n'
        );
        console.error('2. If using Docker Compose, default is:');
        console.error(
          '   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/myoro_arbihawk\n'
        );
      } else if (
        errorCode === '3D000' ||
        errorMessage.includes('does not exist')
      ) {
        console.error('\n❌ Database does not exist!');
        console.error('The database needs to be created.\n');
        console.error('To fix:');
        console.error('1. Run: bun run db:setup');
        console.error('2. Or manually: createdb -U postgres myoro_arbihawk\n');
      } else if (
        errorMessage.includes('relation') &&
        errorMessage.includes('does not exist')
      ) {
        console.error('\n❌ Database tables do not exist!');
        console.error('Migrations need to be run.\n');
        console.error('To fix:');
        console.error('1. Run: bun run db:migrate');
        console.error('2. Or run full setup: bun run setup\n');
      } else {
        console.error('\n❌ Database error:', errorCode);
        console.error('Check your DATABASE_URL and PostgreSQL connection.\n');
      }
    } else {
      console.error('\n❌ Unknown error occurred');
      console.error('Check your DATABASE_URL and PostgreSQL connection.\n');
    }

    process.exit(1);
  }
}

// Run seed if this file is executed directly
// This check works when running with: bun run src/db/seed.ts
if (process.argv[1]?.endsWith('seed.ts')) {
  runSeed();
}
