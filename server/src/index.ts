import { cors } from '@elysiajs/cors';
import { trpc } from '@elysiajs/trpc';
import { Elysia } from 'elysia';
import { appRouter } from './trpc/routers/_app';
import { createContext } from './trpc/context';

const app = new Elysia()
  .use(cors({ origin: true, credentials: true }))
  .use(
    trpc(appRouter, {
      createContext: async ({ headers }) => createContext(headers),
    })
  )
  .listen(3001);

console.log(`🚀 Server is running at http://localhost:${app.server?.port}`);

