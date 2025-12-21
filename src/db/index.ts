import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

/**
 * PostgreSQL connection string.
 *
 * Falls back to default local connection if DATABASE_URL env var is not set.
 * For Docker Compose, use: postgresql://postgres:postgres@localhost:5432/myoro_arbihawk
 */
const connectionString =
  process.env.DATABASE_URL ||
  'postgresql://postgres:postgres@localhost:5432/myoro_arbihawk';

/**
 * PostgreSQL client instance.
 *
 * Handles the actual database connection and query execution.
 * Configured with connection pooling for better performance.
 */
const client = postgres(connectionString, {
  max: 10, // Maximum number of connections in the pool
  idle_timeout: 20, // Close idle connections after 20 seconds
  connect_timeout: 10, // Connection timeout in seconds
});

/**
 * Drizzle ORM database instance.
 *
 * Use this to perform database queries with full type safety.
 * All table schemas are automatically typed based on src/db/schema.ts.
 *
 * @example
 * ```typescript
 * import { db } from '@/db';
 * import { users } from '@/db/schema';
 *
 * const allUsers = await db.select().from(users);
 * ```
 */
export const db = drizzle(client, { schema });
