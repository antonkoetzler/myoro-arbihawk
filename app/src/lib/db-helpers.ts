/**
 * Database query helper utilities.
 *
 * Provides common patterns for database operations to reduce repetition.
 */

/**
 * Finds a single record or throws an error.
 *
 * @param query - Promise that resolves to an array of results
 * @param errorMessage - Error message to throw if no record found
 * @returns The first record from the query result
 * @throws {Error} If no record is found
 *
 * @example
 * ```typescript
 * const user = await findOneOrThrow(
 *   db.select().from(users).where(eq(users.id, userId)),
 *   'User not found'
 * );
 * ```
 */
export async function findOneOrThrow<T>(
  query: Promise<T[]>,
  errorMessage: string
): Promise<T> {
  const results = await query;
  if (results.length === 0) {
    throw new Error(errorMessage);
  }
  const result = results[0];
  if (result === undefined) {
    throw new Error(errorMessage);
  }
  return result;
}

/**
 * Finds a single record or returns null.
 *
 * @param query - Promise that resolves to an array of results
 * @returns The first record from the query result, or null if not found
 *
 * @example
 * ```typescript
 * const user = await findOneOrNull(
 *   db.select().from(users).where(eq(users.id, userId))
 * );
 * ```
 */
export async function findOneOrNull<T>(query: Promise<T[]>): Promise<T | null> {
  const results = await query;
  return results[0] ?? null;
}
