import { initTRPC, TRPCError } from '@trpc/server';
import superjson from 'superjson';
import type { Context } from './context';

/**
 * Initializes tRPC with context and superjson transformer.
 *
 * Superjson allows serialization of complex types (Dates, BigInt, etc.)
 * between client and server.
 */
const t = initTRPC.context<Context>().create({
  transformer: superjson,
});

/**
 * Creates a new tRPC router.
 *
 * Use this to define your API routes and group related procedures.
 */
export const router = t.router;

/**
 * Public tRPC procedure that anyone can call without authentication.
 *
 * Use for endpoints like signup, login, or public data.
 */
export const publicProcedure = t.procedure;

/**
 * Protected tRPC procedure that requires authentication.
 *
 * Automatically checks if a valid JWT token is present in the request.
 * Throws UNAUTHORIZED error if no user is authenticated.
 *
 * @throws {TRPCError} If ctx.userId is null/undefined
 *
 * @example
 * ```typescript
 * export const myRouter = router({
 *   getProfile: protectedProcedure.query(({ ctx }) => {
 *     // ctx.userId is guaranteed to be a string here
 *     return getUserProfile(ctx.userId);
 *   }),
 * });
 * ```
 */
export const protectedProcedure = t.procedure.use(({ ctx, next }) => {
  if (!ctx.userId) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }
  return next({
    ctx: {
      ...ctx,
      userId: ctx.userId,
    },
  });
});
