import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { createUser, findUserByEmail, verifyPassword } from '../../lib/auth';
import { createToken } from '../../lib/jwt';
import { publicProcedure, router } from '../trpc';

const signupSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string(),
});

export const authRouter = router({
  signup: publicProcedure
    .input(signupSchema)
    .mutation(async ({ input }) => {
      const existingUser = await findUserByEmail(input.email);
      if (existingUser) {
        throw new TRPCError({
          code: 'CONFLICT',
          message: 'User already exists',
        });
      }

      const user = await createUser(input.email, input.password);
      const token = createToken(user.id);

      return {
        token,
        user: {
          id: user.id,
          email: user.email,
        },
      };
    }),

  login: publicProcedure
    .input(loginSchema)
    .mutation(async ({ input }) => {
      const user = await findUserByEmail(input.email);
      if (!user) {
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Invalid credentials',
        });
      }

      const isValid = await verifyPassword(input.password, user.passwordHash);
      if (!isValid) {
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Invalid credentials',
        });
      }

      const token = createToken(user.id);

      return {
        token,
        user: {
          id: user.id,
          email: user.email,
        },
      };
    }),
});

