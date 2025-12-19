import { verifyToken } from '../lib/jwt';

export const createContext = async (headers: Headers) => {
  const authHeader = headers.get('authorization');
  const token = authHeader?.replace('Bearer ', '');
  
  let userId: string | null = null;
  if (token) {
    const payload = verifyToken(token);
    userId = payload?.userId || null;
  }

  return {
    userId,
  };
};

export type Context = Awaited<ReturnType<typeof createContext>>;

