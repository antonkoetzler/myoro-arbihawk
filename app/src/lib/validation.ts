import { z } from 'zod';

/**
 * Validates data against a Zod schema and throws if invalid.
 *
 * @param schema - Zod schema to validate against
 * @param data - Data to validate
 * @returns Validated and typed data
 * @throws {z.ZodError} If validation fails
 *
 * @example
 * ```typescript
 * const schema = z.object({ email: z.string().email() });
 * const validData = validateOrThrow(schema, { email: 'test@example.com' });
 * // validData is typed as { email: string }
 * ```
 */
export function validateOrThrow<T>(schema: z.ZodSchema<T>, data: unknown): T {
  return schema.parse(data);
}
