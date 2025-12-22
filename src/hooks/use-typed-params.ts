import { useParams } from 'next/navigation';
import { z } from 'zod';

/**
 * Type-safe hook for accessing URL parameters.
 *
 * Validates params with Zod schema and returns typed values.
 * Throws error if params don't match schema (fail fast).
 *
 * @param schema - Zod schema defining expected params
 * @returns Validated and typed params object
 *
 * @example
 * ```typescript
 * const params = useTypedParams(
 *   z.object({ leagueId: z.string().uuid() })
 * );
 * // params.leagueId is typed as string
 * ```
 */
export function useTypedParams<T extends z.ZodType>(schema: T): z.infer<T> {
  const params = useParams();
  return schema.parse(params);
}
