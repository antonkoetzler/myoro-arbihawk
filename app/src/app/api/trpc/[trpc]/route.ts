import { fetchRequestHandler } from '@trpc/server/adapters/fetch';
import { appRouter } from '@/server/routers/_app';
import { createContext } from '@/server/context';

/**
 * Next.js API route handler for tRPC requests.
 *
 * This function processes all tRPC API calls by:
 * 1. Receiving the HTTP request
 * 2. Creating the tRPC context (with auth info)
 * 3. Routing to the appropriate tRPC procedure
 * 4. Returning the response
 *
 * @param req - The incoming HTTP request from Next.js
 * @returns Promise resolving to the tRPC response
 */
const handler = (req: Request) =>
  fetchRequestHandler({
    endpoint: '/api/trpc',
    req,
    router: appRouter,
    createContext: async () => createContext(req.headers),
  });

export { handler as GET, handler as POST };
