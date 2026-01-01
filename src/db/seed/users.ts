import { eq } from 'drizzle-orm';
import { db } from '../index';
import { users } from '../schema';
import { hashPassword } from '../../lib/auth';

/**
 * Seed data for test users.
 */
const testUsers = [
  { email: 'admin@example.com', password: 'admin123' },
  { email: 'user@example.com', password: 'user123' },
];

/**
 * Seeds users table with test data.
 *
 * @returns Record mapping email to user ID
 */
export async function seedUsers(): Promise<Record<string, string>> {
  console.log('[seed]: \n📝 Creating users...');
  const userIds: Record<string, string> = {};

  for (const { email, password } of testUsers) {
    const existing = await db
      .select()
      .from(users)
      .where(eq(users.email, email))
      .limit(1);

    if (existing.length > 0) {
      const existingUser = existing[0];
      if (existingUser) {
        console.log(`[seed]: ⏭️  User ${email} already exists`);
        userIds[email] = existingUser.id;
        continue;
      }
    }

    const passwordHash = await hashPassword(password);
    const [user] = await db
      .insert(users)
      .values({ email, passwordHash })
      .returning();
    if (!user) {
      throw new Error(`Failed to create user: ${email}`);
    }
    userIds[email] = user.id;
    console.log(`[seed]: ✅ Created user: ${email} / ${password}`);
  }

  return userIds;
}
