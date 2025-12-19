import { protectedProcedure, publicProcedure, router } from '../trpc';
import { authRouter } from './auth';

export const appRouter = router({
  auth: authRouter,
  hello: protectedProcedure.query(() => ({
    greeting: 'Hello World',
  })),
});

export type AppRouter = typeof appRouter;

