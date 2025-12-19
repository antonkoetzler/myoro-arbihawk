import { initTRPC } from '@trpc/server';
import { z } from 'zod';
import { db } from '../db';

const t = initTRPC.create();

export const router = t.router;
export const publicProcedure = t.procedure;

export const appRouter = router({
  // Counter procedures
  counter: router({
    get: publicProcedure.query(async () => {
      let counter = await db.counter.findFirst();
      if (!counter) {
        counter = await db.counter.create({ data: { value: 0 } });
      }
      return counter;
    }),

    increment: publicProcedure.mutation(async () => {
      let counter = await db.counter.findFirst();
      if (!counter) {
        counter = await db.counter.create({ data: { value: 1 } });
      } else {
        counter = await db.counter.update({
          where: { id: counter.id },
          data: { value: counter.value + 1 },
        });
      }
      return counter;
    }),

    decrement: publicProcedure.mutation(async () => {
      let counter = await db.counter.findFirst();
      if (!counter) {
        counter = await db.counter.create({ data: { value: -1 } });
      } else {
        counter = await db.counter.update({
          where: { id: counter.id },
          data: { value: counter.value - 1 },
        });
      }
      return counter;
    }),

    reset: publicProcedure.mutation(async () => {
      let counter = await db.counter.findFirst();
      if (!counter) {
        counter = await db.counter.create({ data: { value: 0 } });
      } else {
        counter = await db.counter.update({
          where: { id: counter.id },
          data: { value: 0 },
        });
      }
      return counter;
    }),
  }),

  // User procedures (example)
  user: router({
    list: publicProcedure.query(async () => {
      return db.user.findMany();
    }),

    create: publicProcedure
      .input(z.object({ email: z.string().email(), name: z.string().optional() }))
      .mutation(async ({ input }) => {
        return db.user.create({ data: input });
      }),
  }),
});

export type AppRouter = typeof appRouter;

