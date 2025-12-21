import { protectedProcedure, router } from '../trpc';
import { authRouter } from './auth';
import { stripeRouter } from './stripe';
import { leaguesRouter } from './leagues';
import { subscriptionsRouter } from './subscriptions';
import { matchesRouter } from './matches';
import { statsRouter } from './stats';
import { bettingRouter } from './betting';

/**
 * Main tRPC router that combines all sub-routers.
 *
 * This is the root router that defines all available API endpoints.
 * Import this type in your frontend to get full TypeScript autocomplete.
 *
 * @example
 * ```typescript
 * // Frontend usage
 * trpc.auth.signup.useMutation();
 * trpc.hello.useQuery();
 * trpc.stripe.createCheckout.useMutation();
 * ```
 */
export const appRouter = router({
  auth: authRouter,
  stripe: stripeRouter,
  leagues: leaguesRouter,
  subscriptions: subscriptionsRouter,
  matches: matchesRouter,
  stats: statsRouter,
  betting: bettingRouter,
  hello: protectedProcedure.query(() => ({
    greeting: 'Hello World', // TODO: Use i18n when backend supports it
  })),
});

/**
 * Type export for the main router.
 *
 * Used by the frontend tRPC client to infer all available procedures and their types.
 */
export type AppRouter = typeof appRouter;
