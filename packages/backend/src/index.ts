import { Elysia } from 'elysia';
import { cors } from '@elysiajs/cors';
import { trpc } from '@elysiajs/trpc';
import { appRouter } from './trpc';

const app = new Elysia()
  .use(cors())
  .use(trpc(appRouter))
  .get('/health', () => ({ status: 'ok' }))
  .listen(3000);

console.log(`🦊 Server running at http://localhost:${app.server?.port}`);

export { appRouter, type AppRouter } from './trpc';

